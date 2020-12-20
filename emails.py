import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email
from python_http_client.exceptions import HTTPError
import config 
import pandas as pd

def ticker_check_email(addTicker, removeTicker):
    html_content = '''<h1> Ticker Changes Required </h1>

    <br>

    <h2> Add the following tickers </h2>
        {}

    <h2> Remove the following Tickers </h2>
        {}
    '''.format(addTicker, removeTicker)
    subject = "Ticker Changes, {}".format(pd.to_datetime('today').strftime('%Y-%m-%d'))
    return (html_content, subject)


def daily_trades(tradesDF):
    htmlTradeDF = tradesDF.to_html()
    html_content = '''<h1> Filled Trades  </h1>

    <br>

    <h2> Trades filled & submitted  </h2>
        {}

    '''.format(htmlTradeDF)
    subject = "Trades for {}".format(pd.to_datetime('today').strftime('%Y-%m-%d'))
    return (html_content, subject)


def send_email(request, html_content, subject):

    sg = SendGridAPIClient('{}'.format(config.SG_KEY))

    message = Mail(
        to_emails="",
        from_email=Email('', "tradingbot"),
        subject=subject,
        html_content=html_content
        )

    try:
        response = sg.send(message)
        return f"email.status_code={response.status_code}"
        #expected 202 Accepted

    except HTTPError as e:
        return e.message
