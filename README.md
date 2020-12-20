# Trading Bot using GCP & TD Ameritrade API

## About the Equity Trading Bot

The 'bot' is deployed as a Cloud Function and runs every weekday morning immediately prior to the market open.  Using the Cloud Scheduler the function is initiated using the `Trading` message at 9:25 ET and goes to collect historical data on _almost_ all the stocks in the S&P500 from the API.  This takes about ~4 minutes & 30 seconds, at which point it then pauses until 9:30am ET.  At exactly 9:30:01 (I wait 1 seconds after the Open) I call the API again to get the current market prices. Once the machine has the opening prices, it calculates metrics to determine which stocks to buy and sell, then it sends all the buy/sell orders in.  

The bot is typically finished with sending all the orders by 9:30:30 (w/in 30 seconds of the market open), usually earlier. The amount of time it takes for the bot to run to completion depends on how many orders it needs to send. As an example, one morning it sent orders for   If it needed to send an order for every stock in consideration, it would take ~30 seconds to complete all the orders (495 stock).  Therefore at most it would be finished by ~9:30:50, which is not terrible - 495 orders in under a minute. 

An example of the bots general processes

- 9:25:00, get historical prices
- 9:30:00, market opens 
- 9:30:01, get current market prices, calculate metrics
- 9:30:20, finished calculating trade metrics, start sending orders
- 9:30:21 - 9:30:50, finished sending _N_ buy & sell orders


## Strategy / Algorithm

The general idea behind this strategy is capitalize on momentum.  The trade decisions for each stock are based on the slope of the 9-day exponential moving average. The slope is calculated using the past three periods of market open prices (including that day's open price).  If the slope is positive, then the stock is trending up, if the slope is negative then the stock is trending down.  The strategy is also set to only buy a stock if the prior period was slope was negative. The idea is to capture stocks that are transitioning into an updward trend.  This means I might miss stocks that are currently in an upward trend (upon deployment), however I'm willing to forego the inital investment to be conservative.  

This is a Long-Only strategy and each stock is weighted the same.  This means that I'm buying the same number of shares for every stock in the universe of stocks I consider.  I understand there are downsides to this, the primary one is that higher priced stocks will contribute more to the overall PnL.  As a result I've removed some stocks from the S&P 500 with high price tags. 





## File Structure & General Info

The way that Google Cloud Funcions are triggered is that they receive a 'message' that is sent to them from a scheduler into the `main.py` file. Therefore `main.py` is the entry point of the bot, and the heart of the bot is in the `utils.py` file. 

- The `main.py` is the entry point of the bot. There are several messages that are currently sent: 1) Check for ticker changes in the index, 2) Find and executing the trades, 3) Submit executed trades to the DB, 4) Shut it all down, sell everything, and 5) Get a new refresh token for the API, which expires every 90 days. 
 -- 
- The `utils.py` file contains the functions to pull the quotes, calculate the historical metrics to make trade decisions, as well as the functions that send the buy/sell orders.  
- The `emails.py` contains functions for sending email notifications.  I'm currently sending emails a few times throughout the day that show executed trades - this captures any trades the bot executes as well as any descretionary trades I place through the TDA website. I also send emails when the composition of the S&P 500 index changes. 
- The `db.py` file contains helper functions for saving data to Google BigQuery.  I'm currently only saving orders to BigQuery, however it can be used to save other data such as the current S&P 500 tickers as well as TDA credentials which change every 90 days. 
- The `config.py` file contains all the configurations the bot needs to execute the various functions. I've removed all the information except the names of the variables. 
- The `tickers.txt` file contains all the current S&P 500 tickers.  The composition of stocks in the S&P 500 occasionally changes, and the easiest / freest way to find the changes (I think) is to simply look at the Wikipedia page of the current tickers.  Every night the bot will go to the Wikipedia page and check for changes in the index.  If there is a change then the file will be updated so that the bot will trade the most relevant tickers.



TODO: 
- Include image of trade decision and historical PnL vs Buy & Hold
- Save tickers in DB instead of a txt file to maintain a history
- Save TDA credentials in DB 
- If a ticker is removed from the index and I'm currently long, the next day(s) the bot won't know to sell. This is where saving tickers in the DB will be helpful. 
