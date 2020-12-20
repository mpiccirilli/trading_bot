# Trading Bot using GCP & TD Ameritrade API

## About the Equity Trading Bot

The 'bot' is deployed as a Cloud Function and runs every weekday morning immediately prior to the market open.  Using the Cloud Scheduler the function is initiated using the `Trading` message at 9:25 ET and goes to collect historical data on _almost_ all the stocks in the S&P500 from the API.  This takes about ~4 minutes & 30 seconds, at which point it then pauses until 9:30am ET.  At exactly 9:30:01 (I wait 1 seconds after the Open) I call the API agian to get the current market prices. Once the machine has the opening prices, it calculates metrics to determine which stocks to buy and sell, then it sends all the buy/sell orders in.  

The bot is typically finished with sending all the orders by 9:30:30 (w/in 30 seconds of the market open), usually earlier. The amount of time it takes for the bot to run to completion depends on how many orders it needs to send.  If it needed to send an order for every stock in consideration, it would take ~30 seconds to complete all the orders (495 stock).  Therefore at most it would be finished by ~9:30:50, which is not terrible - 495 orders in under a minute. 

An example of the bots general processes

- 9:25:00, get historical prices
- 9:30:00, market opens 
- 9:30:01, get current market prices, calculate metrics
- 9:30:20, finished calculating trade metrics, start sending orders
- 9:30:30, finished sending _N_ buy/sell orders


## Strategy / Algorithm

The general idea behind this strategy is capitalize on momentum.  The trade decisions for each stock are based on the slope of the 9-day exponential moving average. The slope is calculated using the past three periods of market open prices (including that day's open price).  If the slope is positive, then the stock is trending up, if the slope is negative then the stock is trending down.  The strategy is also set to only buy a stock if the prior period was slope was negative. The idea is to capture stocks that are transitioning into an updward trend.  This means I might miss stocks that are currently in an upward trend (upon deployment), however I'm willing to forego the inital investment to be conservative.  

This is a Long-Only stratgey and each stock is weighted the same.  This means that I'm buying the same number of shares for every stock in the universe of stocks I consider.  I understand there are downsides to this, the primary one is that higher priced stocks will contribute more to the overall PnL.  As a result I've removed some stocks from the S&P 500 with high price tags. 



TODO: Include image of trade decision and historial PnL

