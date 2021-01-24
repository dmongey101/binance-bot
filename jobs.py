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

    coins = ['BTC', 'ETH']

    for coin in coins:
        print('Getting data from {0} sheet'.format(coin))
        result = service.spreadsheets().values().get(
            spreadsheetId=risk_strategy_sheet_id, range='{0}!A1:E'.format(coin), valueRenderOption='FORMULA').execute()
        current_risk_sheet = result.get('values', [])
        print('{0} rows retrieved.'.format(len(current_risk_sheet)))

        body = {
                'values': current_risk_sheet
            }
            
        # only archive btc for now
        if coin == 'BTC':
            print('Archiving BTC sheet')
            today = date.today().strftime("%b-%d-%Y")
            title = 'BTC ' + today
            archiving_body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': title,
                    }
                }
            }]
            }

            # archive BTC sheet
            print('Creating new sheet {}'.format(title))
            result = service.spreadsheets().batchUpdate(
                spreadsheetId=binance_bot_sheet_id,
                body=archiving_body).execute()

            
            print('Copying data to archived sheet')
            result = service.spreadsheets().values().update(
                spreadsheetId=binance_bot_sheet_id, range= title + '!A1:E',
                valueInputOption='USER_ENTERED', body=body).execute()
            print('{0} cells updated.'.format(result.get('updatedCells')))

        print('Updating the current {0} sheet'.format(coin))
        result = service.spreadsheets().values().update(
            spreadsheetId=binance_bot_sheet_id, range='{0}Main!A1:E'.format(coin),
            valueInputOption='USER_ENTERED', body=body).execute()
        print('{0} cells updated.'.format(result.get('updatedCells')))
    print('Job complete')

def send_daily_email():
    print('Starting daily email job')
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    client = Client(api_key, api_secret)
    client.API_URL = 'https://testnet.binance.vision/api'

    print('Gathering balances')
    balance_table_body = ''
    balances = client.get_account().get('balances')
    for coin in balances:
        asset = coin.get('asset')
        free = coin.get('free')
        locked = coin.get('locked')
        balance_table_body += '<tr><td>{0}</td><td>{1}</td><td>{2}</td></tr>'.format(asset, free, locked)
    
    print('Calculating total USDT balance')
    values = []
    total_usdt_balance = 0.0
    for price in balances:
        if price.get('free') not in ['0.00000000', '0.00'] and price.get('asset') not in ['BUSD', 'USDT']:
            coin = price.get('asset')
            avg_price = client.get_avg_price(symbol=coin+'USDT')
            struct = {}
            struct['coin'] = coin
            struct['price'] = float(avg_price.get('price'))
            struct['amount'] = float(price.get('free'))
            values.append(struct)
            total_usdt_balance += float(avg_price.get('price')) * float(price.get('free'))
        if price.get('asset') == 'USDT':
            total_usdt_balance += float(price.get('free'))
    
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
        <h4>Balances</h4>
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
        <h4>Total USDT balance</h4>
        <table border="1">
            <thead>
                <tr>
                <th>USDT Balance</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                <td>{1}</td>
                </tr>
            </tbody>
        </table>
        <br>   
        <h4>Current Orders</h4>
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
                {2}
            </tbody>
        </table>
    </body>
    </html>
    """.format(balance_table_body, total_usdt_balance, order_table_body)


    port = 465
    gmail_password = os.getenv('GMAIL_PASSWORD')
    # Create a secure SSL context
    context = ssl.create_default_context()

    sender_email = "binancebottest92@gmail.com"
    receiver_emails = ["donalmongey@gmail.com"]
    message = MIMEMultipart("alternative")
    message["Subject"] = "Bot test"
    message["From"] = sender_email

    part1 = MIMEText(html, "html")
    message.attach(part1)

    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        print('Logging into email server')
        server.login(sender_email, gmail_password)
        print('Sending email')
        for email_address in receiver_emails:
            message["To"] = email_address
            server.sendmail(
                sender_email, email_address, message.as_string()
            )
            print('Email sent to {0}'.format(email_address))