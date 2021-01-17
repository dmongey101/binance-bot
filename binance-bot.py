import os
import os.path
import time
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

risk_cool_off_value = float(input('What is the current risk?'))

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_current_price(from_currency, to_currency):
    alpha_base_url = os.getenv('ALPHA_BASE_URL')
    alpha_api_key = os.getenv('ALPHA_API_KEY')
    url = alpha_base_url + 'query?function=CURRENCY_EXCHANGE_RATE&from_currency=' + from_currency + '&to_currency=' + to_currency + '&apikey=' + alpha_api_key
    response = requests.get(url).json()
    return response.get('Realtime Currency Exchange Rate', {}).get('5. Exchange Rate')

def get_current_risks():
    global data, service
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

    # Don't need this for now. Will probaly need it to track buy and sells
    # sheet = service.spreadsheets()
    # result_input = sheet.values().get(spreadsheetId=risk_strategy_sheet_id,
    #                             range=risk_strategy_sheet_range).execute()
    # data_to_copy = result_input.get('values', [])

    current_btc_price = get_current_price("BTC", "USD")    
    values = [
        [
            current_btc_price
        ]
    ]
    body = {
        'values': values
    }

    result = service.spreadsheets().values().update(
        spreadsheetId=binance_bot_sheet_id, range=binance_bot_sheet_range,
        valueInputOption='USER_ENTERED', body=body).execute()
    print('{0} cell updated with price {1}'.format(result.get('updatedCells'), current_btc_price))

    sheet = service.spreadsheets()
    result_input = sheet.values().get(spreadsheetId=binance_bot_sheet_id,
                                range='Binance-bot!B3').execute()
    btc_risk = result_input.get('values', [])

    if not result_input and not values_expansion:
        print('No data found.')

    return btc_risk[0][0]

def btc_sell_order(current_btc_risk):
    usdt_balance = client.get_asset_balance(asset='USDT')
    print('Your USDT balance was {} USDT'.format(usdt_balance.get('free')))
    order = client.order_market_sell(
        symbol='BTCUSDT',
        quantity=0.1)
    print(order)
    usdt_balance = client.get_asset_balance(asset='USDT')
    print('Your USDT balance is now {} USDT'.format(usdt_balance.get('free')))
    print('Sold 0.01 BTC')
    btc_balance = client.get_asset_balance(asset='BTC')
    print('Your BTC balance is now {} BTC'.format(btc_balance.get('free')))
    risk_cool_off_value = btc_risk

def btc_buy_order(current_btc_risk):
    usdt_balance = client.get_asset_balance(asset='USDT')
    print('Your USDT balance was {} USDT'.format(usdt_balance.get('free')))
    order = client.order_market_buy(
        symbol='BTCUSDT',
        quantity=0.1)
    print(order)
    usdt_balance = client.get_asset_balance(asset='USDT')
    print('Your USDT balance is now {} USDT'.format(usdt_balance.get('free')))
    print('Sold 0.01 BTC')
    btc_balance = client.get_asset_balance(asset='BTC')
    print('Your BTC balance is now {} BTC'.format(btc_balance.get('free')))
    risk_cool_off_value = btc_risk

while True:
    print('Last buy/sell risk: {}'.format(risk_cool_off_value))
    btc_risk = get_current_risks()
    print('Current BTC risk: {}'.format(btc_risk))
    if float(btc_risk) - risk_cool_off_value >= 0.025:
        btc_sell_order(float(btc_risk))
    if risk_cool_off_value - float(btc_risk) >= 0.025:
        btc_buy_order(float(btc_risk))

    # I think the alpha api gets updated every minute so I'll probably change this
    time.sleep(30.0 - ((time.time() - starttime) % 30.0))