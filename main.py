import base64

import utils 
import config
import db
import emails
import pandas as pd

import aiohttp
import asyncio



def main(event, context):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')

    ####################################
    ########## Check tickers ###########
    ####################################
    if pubsub_message == 'Ticker':
        print('Getting list of predefined tickers')
        defaultTickers = pd.read_csv('tickers.txt')
        defaultTickerSet = set(defaultTickers['tickers'].values.tolist())

        print("Going to Wikipedia to get list of current tickers in S&P500")
        wikiTickers = utils.get_sp500_tickers()

        # Need to filter out anything with a period.
        filteredWikiTickers = [x for x in wikiTickers if '.' not in x]

        # Now double check to make sure there's a max of 4 letters, remove otherwise
        finalWikiTickers = [x for x in filteredWikiTickers if len(x)<=4]
        wikiTickerSet = set(finalWikiTickers)

        # Check if website tickers are different:
        defaultNotInWiki = defaultTickerSet.difference(wikiTickerSet)
        wikiNotInDefault = wikiTickerSet.difference(defaultTickerSet)

        removeTicker = pd.DataFrame({'RemoveTickers': list(defaultNotInWiki)})

        addTicker = pd.DataFrame({'AddTickers': list(wikiNotInDefault)})

        if ((len(removeTicker)>0) | (len(addTicker)>0)):
            print('Need to change some tickers..')
            html, subject = emails.ticker_check_email(addTicker.to_html(), removeTicker.to_html())
            response = emails.send_email(request=pubsub_message, html_content=html, subject=subject)
            print(response)
        else:
            print("No tickers to change")
        
    ########################################
    ########## Run trading algo ###########
    ########################################
    if pubsub_message == 'Trading':

        # Get Tickers: 
        print('getting tickers')
        tickers = pd.read_csv('tickers.txt')
        tickers = tickers['tickers'].values.tolist()


        print('getting access token')
        newAccess = utils.get_access_token()
        access_token = newAccess['access_token']
        expires_in = newAccess['expires_in']

        print('Running the algo..')
        hist_stock_data = utils.get_stocks(token=access_token, tickers=tickers, expires_in=expires_in)
        print('Calculating trade metrics..')
        trade_metric_df = utils.calc_trade_metrics(stock_data=hist_stock_data)
        print('Shape of trade metrics: ', trade_metric_df.shape)

        print("Getting buy/sell symbols...")
        (algoBuys, algoSells) = utils.find_trades(data_frame=trade_metric_df, token=access_token, tickers=tickers)
        
        print('Submit the orders!')
        # This is the old way - the slow way!
        #(buys, sells) = utils.make_trades(positionsToBuy=algoBuys, positionsToSell=algoSells, token=access_token)

        # Async order submissions
        orderStart = pd.to_datetime('today')
        asyncio.run(utils.make_trades_async(buySymbolsList=algoBuys, sellSymbolsList=algoSells, token=access_token))
        orderEnd = pd.to_datetime('today')
        print('Time took to send orders: ', (orderEnd - orderStart))
        
        buyToday = hist_stock_data[(hist_stock_data['symbol'].isin(algoBuys)  & 
                (hist_stock_data['datetime']==pd.to_datetime('today').strftime('%Y-%m-%d')))]['close'].sum()

        sellToday = hist_stock_data[(hist_stock_data['symbol'].isin(algoSells)  & 
                (hist_stock_data['datetime']==pd.to_datetime('today').strftime('%Y-%m-%d')))]['close'].sum()

        maxNeeded = hist_stock_data[(hist_stock_data['datetime']==pd.to_datetime('today').strftime('%Y-%m-%d'))]['close'].sum()
                         
        print('Approx amount bought today: ', round(buyToday,2))
        print('Approx amount sold today: ', round(sellToday,2))
        print('Maximum possible needed: ', round(maxNeeded,2))
        print('Trading bot deployed')


    #######################################
    #      Save todays trades to DB       #
    #######################################
    if pubsub_message == 'MorningTrades':
        
        print('getting access token')
        newAccess = utils.get_access_token()
        access_token = newAccess['access_token']
        expires_in = newAccess['expires_in']

        print('Pulling and saving todays trades...')
        today = pd.to_datetime('today').strftime('%Y-%m-%d')
        todaysTrades = utils.get_historical_trades_DF(start_date=today, end_date=today, token=access_token)
        print('There were {} trades today..'.format(todaysTrades.shape[0]))

        print('Saving trades to the DB..')
        db.save_trades_gbq(ordersDF=todaysTrades)
        print('Done saving todays trades..')

        html, subject = emails.daily_trades(tradesDF=todaysTrades)
        response = emails.send_email(pubsub_message, html_content=html, subject=subject)
        print('Email response: ', response)
        print('Done saving and send todays trades...')
   


    #######################################
    #           Shut it down!             #
    #######################################
    if pubsub_message == 'Kill':    

        # Get Tickers: 
        print('getting tickers')
        tickers = pd.read_csv('tickers.txt')
        tickers = tickers['tickers'].values.tolist()

        print('getting access token')
        newAccess = utils.get_access_token()
        access_token = newAccess['access_token']

        orderStart = pd.to_datetime('today')
        failures = utils.shut_it_down(token=access_token, tickers=tickers)
        orderEnd = pd.to_datetime('today')
        print('Trades that failed: ', failures)
        print('Time took to send orders: ', (orderEnd - orderStart))


    #######################################
    #        Update Refresh Token         #
    #######################################

    if pubsub_message == 'Refresh Token':

        newAccess = utils.get_access_token()
        access_token = newAccess['access_token']
        
        # Get a new token
        newRefreshToken = utils.get_new_refresh_token(token=access_token)
        print('New creds: ', newRefreshToken)

        configFile = open("config.py").read().splitlines()
        newString = "TD_REFRESH_TOKEN=\'{}\'".format(newRefreshToken['refresh_token'])
        print(newString)

        # Location of token string
        configFile[1] = newString
        with open('config.py', 'w') as f:
            for item in configFile:
                f.write("%s\n" % item)

        print('Saved new refresh token')
