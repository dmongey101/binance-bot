import os
import os.path
import pickle
import ssl, smtplib
from dotenv import load_dotenv
from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from binance.client import Client
from binance.enums import *

load_dotenv()
risk_strategy_sheet_id = os.getenv('RISK_STRATEGY_SHEET_ID')
binance_bot_sheet_id = os.getenv('BINANCE_BOT_SHEET_ID')

def update_sheet_job(service):

    print('Getting data from BTC sheet')
    result = service.spreadsheets().values().get(
        spreadsheetId=risk_strategy_sheet_id, range='BTC!A1:E', valueRenderOption='FORMULA').execute()
    current_risk_sheet = result.get('values', [])
    print('{0} rows retrieved.'.format(len(current_risk_sheet)))

    today = date.today().strftime("%b-%d-%Y")
    title = 'BTC ' + today
    body = {
    'requests': [{
        'addSheet': {
            'properties': {
                'title': title,
            }
        }
    }]
    }

    # archive
    print('Creating new sheet {}'.format(title))
    result = service.spreadsheets().batchUpdate(
        spreadsheetId=binance_bot_sheet_id,
        body=body).execute()

    body = {
        'values': current_risk_sheet
    }
    print('Copying data to archived sheet')
    result = service.spreadsheets().values().update(
        spreadsheetId=binance_bot_sheet_id, range= title + '!A1:E',
        valueInputOption='USER_ENTERED', body=body).execute()
    print('{0} cells updated.'.format(result.get('updatedCells')))

    print('Updating the current sheet')
    result = service.spreadsheets().values().update(
        spreadsheetId=binance_bot_sheet_id, range='BTCMain!A1:E',
        valueInputOption='USER_ENTERED', body=body).execute()
    print('{0} cells updated.'.format(result.get('updatedCells')))
    print('Job complete')

def send_daily_email():
    print('Starting daily email job')
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    client = Client(api_key, api_secret)
    client.API_URL = 'https://testnet.binance.vision/api'

    coins = ['USDT', 'BTC', 'ETH']
    balance_table_body = ''
    balances = {}
    print('Gathering balances')
    for coin in coins:
        balance = client.get_asset_balance(asset=coin)
        asset = balance.get('asset')
        free = balance.get('free')
        locked = balance.get('locked')
        balance_table_body += '<tr><td>{0}</td><td>{1}</td><td>{2}</td></tr>'.format(asset, free, locked)

    symbols = ['BTCUSDT', 'ETHUSDT']
    all_orders = []
    print('Gathering open orders')
    for symbol in symbols:
        orders = client.get_open_orders(symbol=symbol)
        for order in orders:
            all_orders.append(order)
    
    order_table_body = ''

    for order in all_orders:
        symbol = order.get('symbol')
        orderId = order.get('orderId')
        price = order.get('price')
        origQty = order.get('origQty')
        status = order.get('status')
        executedQty = order.get('executedQty')
        order_table_body += '<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td><td>{4}</td><td>{5}</td></tr>'.format(symbol, orderId, price, origQty, status, executedQty)

    html = """\
    <html>
    <body>
        <h2>Balances</h2>
        <table border="1">
            <thead>
                <tr>
                <th>Coin</th>
                <th>Balance</th>
                <th>Locked</th>
                </tr>
            </thead>
            <tbody>
                {0}
            </tbody>
        </table>
        <br>
        <h2>Current Orders</h2>
        <table border="1">
            <thead>
                <tr>
                <th>Symbol</th>
                <th>OrderId</th>
                <th>Limit Price</th>
                <th>Amount to Sell</th>
                <th>Status</th>
                <th>Amount Sold</th>
                </tr>
            </thead>
            <tbody>
                {1}
            </tbody>
        </table>
    </body>
    </html>
    """.format(balance_table_body, order_table_body)


    port = 465
    gmail_password = os.getenv('GMAIL_PASSWORD')
    # Create a secure SSL context
    context = ssl.create_default_context()

    sender_email = "binancebottest92@gmail.com"
    receiver_email = "donalmongey@gmail.com"
    message = MIMEMultipart("alternative")
    message["Subject"] = "Bot test"
    message["From"] = sender_email
    message["To"] = receiver_email

    part2 = MIMEText(html, "html")
    message.attach(part2)

    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        print('Logging into email server')
        server.login(sender_email, gmail_password)
        print('Sending email')
        server.sendmail(
            sender_email, receiver_email, message.as_string()
        )
        print('Email sent')
