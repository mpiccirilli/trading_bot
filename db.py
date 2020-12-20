import config
import pandas as pd
import json

from google.oauth2 import service_account
import pandas_gbq



def _formatTradesForDB(ordersDF):
    # Set the variable types for the DB schema
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


def save_trades_gbq(ordersDF):

    # Need GBQ creds
    credentials = service_account.Credentials.from_service_account_info(config.BQ_CREDS)
    
    # Before we submit, let's make sure we haven't already submitted these trades
    # If there are trades we've submitted, we'll ignore them. 
    query = 'select orderId from {}'.format(config.GBQ_ORDERS_TABLE)
    checkDB = pd.read_gbq(query=query, credentials=credentials)
    
    # Find existing orders in the DB and exclude them from the DB submission
    existInDB = ordersDF.loc[ordersDF['orderId'].isin(checkDB['orderId']),'orderId'].values.tolist()
    ordersDF = ordersDF[~ordersDF['orderId'].isin(existInDB)].reset_index(drop=True)
    ordersForDB = _formatTradesForDB(ordersDF)

    if ordersForDB.shape[0] > 0:
        print('Submitting {} trades to DB..'.format(ordersForDB.shape[0]))
        
        ordersForDB.to_gbq(destination_table='{}'.format(config.GBQ_ORDERS_TABLE),
                        credentials = credentials, if_exists='append')
        
    else:
        print('All trades are already in the DB')
