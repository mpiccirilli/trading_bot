
import config

import pandas as pd
import requests
import json
import numpy as np
from dateutil.relativedelta import relativedelta
import time
import urllib.parse
import re
from bs4 import BeautifulSoup
import aiohttp
import asyncio
from scipy.stats import linregress



########################
### Order functions ####
########################
def make_buy_order(symbol, token):
    url = 'https://api.tdameritrade.com/v1/accounts/{}/orders'.format(config.TD_MARGIN_ACCOUNT)

    order = {
      "orderType": "MARKET",
      "session": "NORMAL",
      "duration": "DAY",
      "orderStrategyType": "SINGLE",
      "orderLegCollection": [
        {
          "instruction": "BUY",
          "quantity": 1,
          "instrument": 
            {
            "symbol": symbol,
            "assetType": "EQUITY"
          }
        }
      ]
    }    
    
    headers= {'Authorization': 'Bearer '+ token}
    r = requests.post(url, json=order, headers=headers)
    return r.status_code
    
    

def make_sell_order(symbol, token):
    url = 'https://api.tdameritrade.com/v1/accounts/{}/orders'.format(config.TD_MARGIN_ACCOUNT)

    order = {
      "orderType": "MARKET",
      "session": "NORMAL",
      "duration": "DAY",
      "orderStrategyType": "SINGLE",
      "orderLegCollection": [
        {
          "instruction": "SELL",
          "quantity": 1,
          "instrument": 
            {
            "symbol": symbol,
            "assetType": "EQUITY"
          }
        }
      ]
    }    
    
    headers= {'Authorization': 'Bearer '+ token}
    r = requests.post(url, json=order, headers=headers)
    return r.status_code



################################
#### GET OPEN MARKET QUOTES ###
################################
def get_quotes(token, tickers):
    allSymbolsEncoded = urllib.parse.quote(','.join(tickers), )

    url = 'https://api.tdameritrade.com/v1/marketdata/quotes??apikey={}&symbol={}'.format(config.TD_CLIENT_ID,
                                                                                         allSymbolsEncoded)
    payload= {'Authorization': 'Bearer '+token}
    
    r = requests.get(url, headers=payload)
    
    return json.loads(r.content)
    

    
#########################
### GET PRICE HISTORY ###
#########################
def get_price_history(ticker, token, start_date, end_date): 
    url = 'https://api.tdameritrade.com/v1/marketdata/{}/pricehistory?apikey={}&periodType=month&frequencyType=daily&startDate={}&endDate={}'.format(
        ticker, 
        config.TD_CLIENT_ID,
        start_date,
        end_date
    )
 
    payload= {'Authorization': 'Bearer '+token}
    r = requests.get(url, data=payload)
    return json.loads(r.content)
    

########################
#### GET POSITIONS ####
########################
def get_positions(token):
    
    # New Account, no margin
    url = 'https://api.tdameritrade.com/v1/accounts/{}?fields=positions'.format(config.TD_MARGIN_ACCOUNT)
    
    payload= {'Authorization': 'Bearer '+token}
    r = requests.get(url, headers=payload)
    
    accountInfo = json.loads(r.content)
    current_positions = []
    try: 
        positions = accountInfo['securitiesAccount']['positions']

        for p in positions: 
            current_positions.append(p['instrument']['symbol'])

        return current_positions
    except:
        return current_positions



##########################
#### GET TRANSACTIONS ####
##########################

def get_transactions(start_date, end_date, token):
    # historical transactions between dates
    url = 'https://api.tdameritrade.com/v1/orders?accountId={}&fromEnteredTime={}&toEnteredTime={}&status=FILLED'.format(
        config.TD_MARGIN_ACCOUNT,
        start_date,
        end_date
    )
    payload= {'Authorization': 'Bearer '+token}
    r = requests.get(url, headers=payload)
    histOrders = json.loads(r.content)
    return histOrders


    
########################
### GET ACCESS TOKEN ###
########################
def get_access_token():
    url = 'https://api.tdameritrade.com/v1/oauth2/token'
    payload = {'grant_type': config.TD_GRANT_TYPE, 
              'client_id': config.TD_CLIENT_ID,
              'refresh_token': config.TD_REFRESH_TOKEN
    }
    r = requests.post(url, data=payload, timeout=10)
    return json.loads(r.content)
   

    
################# 
### GET DATES ###
#################
def get_dates(nMonths = 3):
    today_date = pd.to_datetime('today')

    # Epoch Dates (for TDA API)
    sdate = (pd.to_datetime(today_date) - relativedelta(months=nMonths)).strftime('%s')+'000'
    edate = (pd.to_datetime('today') - pd.Timedelta('1 days')).strftime('%s')+'000'

    # String Dates for loop
    start_date_str = (pd.to_datetime(today_date) - relativedelta(months=nMonths)).strftime('%Y-%m-%d')
    end_date_str = (pd.to_datetime('today') - pd.Timedelta('1 days')).strftime(format='%Y-%m-%d')
    date_range = pd.date_range(start_date_str,end_date_str,freq='d')

    return (today_date, sdate, edate, start_date_str, end_date_str, date_range)



###################
### FIND TRADES ###
###################
def find_trades(data_frame, token, tickers):
    
    stock_data = data_frame.copy(deep=True)

    today = pd.to_datetime('today').strftime('%Y-%m-%d')

    # Get todays trades: 
    print('Finding todays trades..')
    t4 = pd.to_datetime('today')
    
    # If the slope is >= 0 and the prior slope sign is negative, then we're gonna buy
    # 2020-10-12: I removed the prior sign must be negative filter. Very conservative. I want the bull runs. 
    buyTickersDF = stock_data[ (stock_data['slope']>=0) & 
                      (stock_data['datetime']==today) & 
                      (stock_data['prior_slope_sign'] < 0) #Only want those transitioning from sell to buy
                     ]
    
    #
    sellTickersDF = stock_data[ (stock_data['slope']<0) & 
                       (stock_data['datetime']==today)
                      ]

    buySymbols = buyTickersDF['symbol'].values.tolist()
    sellSymbols = sellTickersDF['symbol'].values.tolist()

        
    print('Getting current positions: ')
    current_positions = get_positions(token=token)
    print('Number of current positions: ', len(current_positions))
    print('Positions: ', current_positions)


    print('Getting BUY and SELL orders...')
    
    # If I own nothing, buy them all, and sell nothing
    if ( len(current_positions) == 0): 
        sellSymbols = [] # Dont want to sell anything I don't own!
        t5 = pd.to_datetime('today')
        print("Time spent getting todays trades: ", t5-t4)
        return (buySymbols, sellSymbols)
    
    else: 
        positionsToSell = [s for s in sellSymbols if s in [p for p in current_positions]]
        positionsToBuy = [x for x in buySymbols if x not in [y for y in current_positions]]
        t5 = pd.to_datetime('today')
        print("Time spent getting todays trades: ", t5-t4)
        return (positionsToBuy, positionsToSell)
        


    
###########################
# Make buy and sell orders #
###########################
def make_trades(positionsToBuy, positionsToSell, token):
    t1 = pd.to_datetime('today') 
    print('Buying {} stocks'.format(len(positionsToBuy)))
    print('Positions to buy: ', positionsToBuy)
    print('Selling {} stocks'.format(len(positionsToSell)))
    print('Positions to sell: ', positionsToSell)

    print('Making BUY and SELL orders')
    
    if ( len(positionsToSell) == 0): 

        # No positions to sell so no need to SELL anything
        # But we do still need to buy!
        for b in positionsToBuy: 
            theOrder = make_buy_order(b, token)
            if theOrder!=201:
                print('Failed to BUY: ', b, ', had code: ', theOrder)

    else: 
        # If we do have positions, Let's figure out what needs to be bought/sold: 

        # SELL ORDERS
        print("Number of SELL orders: ", len(positionsToSell))
        if len(positionsToSell) > 0: 

            for s in positionsToSell: 
                theOrder = make_sell_order(s, token)
                if theOrder!=201:
                    print('Failed to SELL: ', s, ', had code: ', theOrder)


        # BUY ORDERS
        print("Number of BUY orders: ", len(positionsToBuy))
        if len(positionsToBuy) > 0:

            for b in positionsToBuy:
                theOrder = make_buy_order(b, token)
                if theOrder!=201:
                    print('Failed to BUY: ', b, ', had code: ', theOrder)


    t2 = pd.to_datetime('today')    
    print('Time to complete orders: ', t2-t1)  

    return (positionsToBuy,positionsToSell)    


async def make_trades_async(buySymbolsList, sellSymbolsList, token):

    print('Symbols to buy: ',len(buySymbolsList), buySymbolsList)
    print('Symbols to sell: ',len(sellSymbolsList), sellSymbolsList)

    buyDict = dict.fromkeys(buySymbolsList, "BUY")
    sellDict = dict.fromkeys(sellSymbolsList, "SELL")
    trades_dict = {**sellDict, **buyDict}
    
    url = 'https://api.tdameritrade.com/v1/accounts/{}/orders'.format(config.TD_MARGIN_ACCOUNT)
    
    async with aiohttp.ClientSession() as session:
        # Sell first
        post_tasks = []
        
        # prepare the coroutines that post
        for ticker, trade_action in trades_dict.items():
            post_tasks.append(do_post(session, url, ticker, trade_action, token))
            
        # now execute them all at once
        await asyncio.gather(*post_tasks)

    
    
async def do_post(session, url, ticker, trade_action, token):
    async with session.post(url, 
                            json ={"orderType": "MARKET",
                                   "session": "NORMAL",
                                    "duration": "DAY",
                                    "orderStrategyType": "SINGLE",
                                    "orderLegCollection": [{
                                          "instruction": trade_action,
                                          "quantity": 30,
                                          "instrument": {
                                            "symbol": ticker,
                                            "assetType": "EQUITY"
                                          }
                                    }]
                                  },
                            headers= {'Authorization': 'Bearer '+ token}
                           ) as response:
        if response.status != 201:
            print("Failed to make trade for {}".format(ticker))
        


##########################
#####  THE WORKHORSE  ####
#####  GET STOCK DATA ####
##########################
def get_stocks(token, tickers, expires_in):

    
    (today_date, 
     sdate, 
     edate, 
     start_date_str, 
     end_date_str, 
     date_range) = get_dates()
    
    
    failure_list=[]
    fullDateDF = pd.DataFrame(columns = ['open', 'close', 'datetime', 'symbol'])
    
    # Get current time.  We'll need to get a new token 
    t1 = pd.to_datetime('today')
    throttleTracker1 = pd.to_datetime('today')
    for n,t in enumerate(tickers):
        
        
        if ( (n>0) & (n % 22 ==0) ):
            print(n)
            if (n % 110 == 0):
                throttleTracker2 = pd.to_datetime('today')
                secondsPassed = (throttleTracker2-throttleTracker1).total_seconds()
                if secondsPassed < 60: 
                    print('Interation: ', n)
                    print('Need to slow down, pausing for : ', 60-secondsPassed, ' seconds')
                    time.sleep(60-secondsPassed)
                    throttleTracker1 = pd.to_datetime('today')

            

        # Determine if we need to get 
        t2 = pd.to_datetime('today')
        seconds_passed = (t2-t1).total_seconds()
        if (seconds_passed > expires_in*.90): 
            print('getting new token')
            print((t2-t1).total_seconds())
            newAccess = get_access_token()
            t1 = pd.to_datetime('today')
            access_token = newAccess['access_token']
            expires_in = newAccess['expires_in']

        symbol = t
        try:

            hist_data = get_price_history(ticker=symbol, 
                                          token=token, 
                                          start_date=int(sdate), 
                                          end_date=int(edate))
            
            hist_data = pd.read_json(json.dumps(hist_data['candles']), orient='records')
            hist_data['datetime'] = pd.to_datetime(hist_data['datetime'].dt.strftime("%Y-%m-%d"))
            hist_data = hist_data.sort_values(by='datetime', ascending=False).reset_index(drop=True)
            hist_data['symbol'] = symbol
            hist_data = hist_data[['open', 'close', 'datetime', 'symbol']]
            
            try: 
                fullDateDF = fullDateDF.append(hist_data, ignore_index=True)
                
            except: 
                print('Failed to combine data for: ', symbol)
                failure_list.append(symbol)

        except:
            print('Couldnt retrieve data for: ', symbol)
            failure_list.append(symbol)
            
    t3 = pd.to_datetime('today')    
    print('Time to finish getting historical data: ', t3-t1)  

    
    # Put in the time delay here to wait 9:30am EST    

    market_open = pd.Timestamp(pd.to_datetime('today').strftime('%Y-%m-%d')+ ' 9:30:01', tz='America/New_York') #Add one second
    current_time = pd.Timestamp(pd.to_datetime('today'), tz='UTC').tz_convert('America/New_York') #UTC by default, convert to Easter
    time_to_wait = (market_open - current_time).total_seconds()
    print('Market opens at: ', market_open)
    print('Current time (Eastern): ', current_time)
    print('Amount of time to wait: ', time_to_wait )
    if (time_to_wait > 0):
        pauseAmount = time_to_wait
        print('pause for {} seconds..'.format(pauseAmount))
        time.sleep(pauseAmount)

    
    
    # Now I need to go get todays data: 
    print('Get todays quotes...')
    current_quotes = get_quotes(token=token, tickers=tickers)
    currentQuoteDF = pd.read_json(json.dumps(current_quotes), orient='index')
    currentQuoteDF = currentQuoteDF[['openPrice', 'lastPrice', 'symbol']].reset_index(drop=True)
    currentQuoteDF['datetime'] = today_date.strftime(format='%Y-%m-%d')
    print(currentQuoteDF)
    currentQuoteDF = currentQuoteDF.rename(columns ={'openPrice': 'open', 'lastPrice': 'close'})
    
    # Put the historical data and the new current market data
    fullDateDF = fullDateDF.append(currentQuoteDF, ignore_index=True, sort=False
                                  ).drop_duplicates().reset_index(drop=True
                                  ).sort_values(by=['symbol', 'datetime'], ascending=False
                                  ).reset_index(drop=True)
    
    fullDateDF['datetime'] = pd.to_datetime(fullDateDF['datetime'])
    
    t4 = pd.to_datetime('today')    
    print('Time spent getting current market quotes: ', t4-t3)  
    
    print("Done!")
    
    return fullDateDF


#############################
#       Trade Metrics       #
#############################

def get_slope(array):
    y = np.array(array)
    x = np.arange(len(y))
    slope, intercept, r_value, p_value, std_err = linregress(x,y)
    return slope

def calc_trade_metrics(stock_data, dayWindow=3):
    
    print('Calculating trade metrics...')
    t1=pd.to_datetime('today')
    # Sort the data first
    stock_data = stock_data.sort_values(by=['symbol', 'datetime'], ascending=True).reset_index(drop=True)
    
    # Now let's start calculating metrics
    stock_data['EMA_Close'] = stock_data.groupby('symbol')['close'].apply(lambda x: x.ewm(span=9).mean())
    stock_data['EMA_Open'] = stock_data.groupby('symbol')['open'].apply(lambda x: x.ewm(span=9).mean())
    
    stock_data = stock_data.sort_values(by=['symbol', 'datetime'], ascending=False).reset_index(drop=True)

    # 3 Day window for calculating the slope
    stock_data['slope'] = stock_data.sort_values(by=['symbol', 'datetime'], ascending=True
                                       ).groupby('symbol')['EMA_Open'
                                       ].rolling(window=dayWindow
                                       ).apply(get_slope, raw=False
                                       ).reset_index(0, drop=True)
    
    
    # This is really only necessary when first starting the model. 
    # What we're doing here is to only buy the stocks that are transitioning from
    # a downward slope to a upward slope.
    # If a stock is already on an upward slope, we're going to skip it. 
    stock_data['prior_slope'] = stock_data.groupby('symbol')['slope'].apply(lambda x: x.shift(-1))
    stock_data['prior_slope_sign'] = np.sign(stock_data['prior_slope'])
    t2=pd.to_datetime('today')
    print('Time calculating todays trades: ', (t2-t1))
    print(stock_data.head(1))
    print(stock_data.tail(1))
    return stock_data



###################
# Historical Trades 
###################

def get_historical_trades_DF(start_date, end_date, token): 
    
    # Get historical trades
    historicalTrades = get_transactions(start_date=start_date, 
                                        end_date=end_date, 
                                        token = token)
    
    # Create the DF
    ordersDF = pd.DataFrame(columns=['accountId', 'closeTime', 'enteredTime', 'filledQuantity' ,
                                 'price', 'orderId', 'orderInstruction', 'symbol', 'positionEffect', 
                                'assetType', 'orderType', 'orderStatus', 'tradeQuantity'])
    
    # Loop through the transactions and save into the DF
    for i, o in enumerate(historicalTrades):
        ordersDF.loc[i, 'accountId'] = o['accountId']
        ordersDF.loc[i, 'closeTime'] = o['closeTime']
        ordersDF.loc[i, 'enteredTime'] = o['enteredTime']
        ordersDF.loc[i, 'filledQuantity'] = o['filledQuantity']

        # TODO: if I begin to order more than 1 share I will need
        #       to loop through the order activitiy execution leegs
        ordersDF.loc[i, 'price'] = o['orderActivityCollection'][0]['executionLegs'][0]['price']
        ordersDF.loc[i, 'orderId'] = o['orderId']
        # TODO: need to loop through order leg connection if have more than 1 share
        ordersDF.loc[i, 'orderInstruction'] = o['orderLegCollection'][0]['instruction']
        ordersDF.loc[i, 'symbol'] = o['orderLegCollection'][0]['instrument']['symbol']
        ordersDF.loc[i, 'positionEffect'] = o['orderLegCollection'][0]['positionEffect']
        ordersDF.loc[i, 'assetType'] = o['orderLegCollection'][0]['orderLegType'] #Asset Type
        ordersDF.loc[i, 'orderType'] = o['orderType']
        ordersDF.loc[i, 'orderStatus'] = o['status']
        ordersDF.loc[i, 'tradeQuantity'] = o['quantity']
         
    # Set the variable types for the DB
    ordersDF['accountId'] = ordersDF['accountId'].astype('int')
    ordersDF['closeTime'] = pd.to_datetime(ordersDF['closeTime'])
    ordersDF['enteredTime'] = pd.to_datetime(ordersDF['enteredTime'])
    ordersDF['filledQuantity'] = ordersDF['filledQuantity'].astype('float')
    ordersDF['price'] = ordersDF['price'].astype('float')
    ordersDF['orderId'] = ordersDF['orderId'].astype('int')
    ordersDF['orderInstruction'] = ordersDF['orderInstruction'].astype('str')
    ordersDF['symbol'] = ordersDF['symbol'].astype('str')
    ordersDF['positionEffect'] = ordersDF['positionEffect'].astype('str')
    ordersDF['assetType'] = ordersDF['assetType'].astype('str')
    ordersDF['orderType'] = ordersDF['orderType'].astype('str')
    ordersDF['orderStatus'] = ordersDF['orderStatus'].astype('str')
    ordersDF['tradeQuantity'] = ordersDF['tradeQuantity'].astype('float')

    return ordersDF
   

###########################
      # Shut it down! #
###########################

def shut_it_down(token, tickers):
    # TODO: make this run async. This sells using the old/slow methods.     
    # Get current positions: 
    print('Getting current positions: ')
    current_positions = get_positions(token=token)
    print('Number of current positions: ', len(current_positions) )
    positionsToSell = [s for s in current_positions if s in [p for p in tickers]]
    print('Number of positions to sell: ', len(positionsToSell) )
    failedToSell = []
    if ( len(positionsToSell) >0):
        for s in positionsToSell: 
                theOrder = make_sell_order(s, token)
                if theOrder!=201:
                    print('Failed to SELL: ', s, ', had code: ', theOrder)
                    failedToSell.append(s)   

    return failedToSell


    
##################################################
            ###### TICKER CHECK ######
##################################################


def get_sp500_tickers():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    page_html = BeautifulSoup(requests.get(url).text, 'lxml')
    stock_table = page_html.find(id='constituents')
    nyse_ticker_elements = page_html.find_all("a", href=re.compile("nyse"))
    nas_ticker_elements = page_html.find_all("a", href=re.compile("nasdaq"))
    all_tickers = nyse_ticker_elements + nas_ticker_elements
    tickers = []
    for t in all_tickers: 
        tickers.append(t.text)
    filtered_tickers = [x for x in tickers if '.' not in x]
    # Now double check to make sure there's a max of 4 letters, remove otherwise
    final_tickers = [x for x in filtered_tickers if len(x)<=4]
    return final_tickers

#######################
## New Refresh Token ##
#######################

def get_new_refresh_token(token):
    url = 'https://api.tdameritrade.com/v1/oauth2/token'
    payload = {'grant_type': config.TD_GRANT_TYPE, 
              'client_id': config.TD_CLIENT_ID,
              'refresh_token': config.TD_REFRESH_TOKEN,
               'access_type': 'offline'
    }
    r = requests.post(url, data=payload, timeout=10)
    return json.loads(r.content)
