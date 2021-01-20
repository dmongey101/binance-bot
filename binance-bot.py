import os
import os.path
import math
import time
import schedule
import json
import pickle
import pandas as pd
import requests
import urllib3
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow,Flow
from google.auth.transport.requests import Request
from binance.client import Client
from binance.enums import *
from dotenv import load_dotenv
from datetime import date
from jobs import update_sheet_job

starttime = time.time()
load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

api_key = os.getenv("BINANCE_API_KEY")
api_secret = os.getenv("BINANCE_API_SECRET")

client = Client(api_key, api_secret)
client.API_URL = 'https://testnet.binance.vision/api'

# here enter the id of your google sheet
risk_strategy_sheet_id = os.getenv("RISK_STRATEGY_SHEET_ID")
risk_strategy_sheet_range = 'BTC!A2:G'

binance_bot_sheet_id = os.getenv('BINANCE_BOT_SHEET_ID')
binance_bot_sheet_range = 'Binance-bot!A3'

risk_cool_off_value = 0.8

servive = None

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_current_price(from_currency, to_currency):
    alpha_base_url = os.getenv('ALPHA_BASE_URL')
    alpha_api_key = os.getenv('ALPHA_API_KEY')
    url = alpha_base_url + 'query?function=CURRENCY_EXCHANGE_RATE&from_currency=' + from_currency + '&to_currency=' + to_currency + '&apikey=' + alpha_api_key
    response = requests.get(url).json()
    return response

def get_current_risks():
    global data, service, current_btc_price
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'test-bot-creds.json', SCOPES) # here enter the name of your downloaded JSON file
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    btc_price_json = get_current_price("BTC", "USD")
    if btc_price_json is None:
        btc_price_json = get_current_price("BTC", "USD")
    
    current_btc_price = float(btc_price_json.get('Realtime Currency Exchange Rate', {}).get('5. Exchange Rate'))
    current_btc_price_time = btc_price_json.get('Realtime Currency Exchange Rate', {}).get('6. Last Refreshed')
       
    values = [
        [
            current_btc_price
        ]
    ]
    body = {
        'values': values
    }
    # updating price in sheet
    result = service.spreadsheets().values().update(
        spreadsheetId=binance_bot_sheet_id, range=binance_bot_sheet_range,
        valueInputOption='USER_ENTERED', body=body).execute()
    print('{0} cell updated with price {1} at {2}'.format(result.get('updatedCells'), "{:.2f}".format(float(current_btc_price)), current_btc_price_time))

    # getting current risk from sheet
    sheet = service.spreadsheets()
    result_input = sheet.values().get(spreadsheetId=binance_bot_sheet_id,
                                range='Binance-bot!B3').execute()
    btc_risk = result_input.get('values', [])

    if not result_input and not values_expansion:
        print('No data found.')

    return float(btc_risk[0][0])

def btc_sell_order(current_btc_risk):
    # this needs to be the initial amount of btc
    btc_holding = float(client.get_asset_balance(asset='BTC').get('free'))
    slo_div = 0.0753 + 0.0897*math.log(current_btc_risk)
    slo_btc_amount = float(format(btc_holding * slo_div, ".5f"))
    slo_price = math.floor(current_btc_price-500)
    print('Looking for previous orders')
    old_order = client.get_open_orders(symbol='BTCUSDT')
    if old_order:
        old_order_id = old_order[0].get('orderId')
        print('Order found with id {}'.format(old_order_id))
        result = client.cancel_order(
            symbol='BTCUSDT',
            orderId=str(old_order_id)
        )
        print('Cancelled order with id {}'.format(old_order_id))
    else:
        print('No order found')
    print('Creating new order')
    print('Quantity: {} BTC'.format(slo_btc_amount))
    print('Sell Price: ${}'.format(slo_price))
    new_order = client.create_order(
        symbol='BTCUSDT',
        side=SIDE_SELL,
        type=ORDER_TYPE_LIMIT,
        timeInForce=TIME_IN_FORCE_GTC,
        quantity=slo_btc_amount,
        price=slo_price
    )
    print('Sell order created')
    global risk_cool_off_value
    risk_cool_off_value += 0.025
    risk_cool_off_value = round(risk_cool_off_value, 3)
    print('New sell order risk is set to {}'.format(risk_cool_off_value))
    
    
def btc_buy_order():
    usdt_balance = client.get_asset_balance(asset='USDT')
    print('Your USDT balance was {} USDT'.format(usdt_balance.get('free')))
    order = client.order_market_buy(
        symbol='BTCUSDT',
        quantity=0.3)
    print(order)
    usdt_balance = client.get_asset_balance(asset='USDT')
    print('Your USDT balance is now {} USDT'.format(usdt_balance.get('free')))
    print('You bought 0.3 BTC')
    btc_balance = client.get_asset_balance(asset='BTC')
    print('Your BTC balance is now {} BTC'.format(btc_balance.get('free')))
    global risk_cool_off_value
    risk_cool_off_value += 0.025
    risk_cool_off_value = round(risk_cool_off_value, 3)
    print('New sell order risk is set to {}'.format(risk_cool_off_value))

# schedule.every().monday.at("09:00").do(update_sheet_job)
schedule.every().day.at("07:00").do(update_sheet_job)

while True:
    schedule.run_pending()
    current_btc_risk = get_current_risks()
    if risk_cool_off_value - current_btc_risk >= 0.05:
        risk_cool_off_value -= 0.025
    print('Current BTC risk: {}'.format(current_btc_risk))
    if current_btc_risk >= risk_cool_off_value:
        btc_sell_order(current_btc_risk)
    if current_btc_risk <= 0.5:
        btc_buy_order()
    print('----------------------------')
    # I think the alpha api gets updated every minute so I'll probably change this
    time.sleep(60.0 - ((time.time() - starttime) % 60.0))