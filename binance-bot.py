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
from dotenv import load_dotenv
from datetime import date
from jobs import update_sheet_job, send_daily_email
from buy_and_sell import sell_order, buy_order

starttime = time.time()
load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# here enter the id of your google sheet
risk_strategy_sheet_id = os.getenv("RISK_STRATEGY_SHEET_ID")
binance_bot_sheet_id = os.getenv('BINANCE_BOT_SHEET_ID')

risk_cool_off_btc_value = 0.75
risk_cool_off_eth_value = 0.575

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
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

def get_current_price(from_currency, to_currency):
    alpha_base_url = os.getenv('ALPHA_BASE_URL')
    alpha_api_key = os.getenv('ALPHA_API_KEY')
    url = alpha_base_url + 'query?function=CURRENCY_EXCHANGE_RATE&from_currency=' + from_currency + '&to_currency=' + to_currency + '&apikey=' + alpha_api_key
    response = requests.get(url).json()
    return response

def get_current_risks(from_currency, to_currency):
    global current_price

    coin_price_json = get_current_price(from_currency, to_currency)
    if coin_price_json is None:
        coin_price_json = get_current_price(from_currency, to_currency)
    
    current_price = float(coin_price_json.get('Realtime Currency Exchange Rate', {}).get('5. Exchange Rate'))
    current_price_time = coin_price_json.get('Realtime Currency Exchange Rate', {}).get('6. Last Refreshed')   
    values = [
        [
            current_price
        ]
    ]
    body = {
        'values': values
    }
    # updating price in sheet
    result = service.spreadsheets().values().update(
        spreadsheetId=binance_bot_sheet_id, range=from_currency+'Main!A3',
        valueInputOption='USER_ENTERED', body=body).execute()
    print('{0} cell updated with price {1}{2} at {3}'.format(result.get('updatedCells'), "{:.2f}".format(float(current_price)), from_currency, current_price_time))

    # getting current risk from sheet
    sheet = service.spreadsheets()
    result_input = sheet.values().get(spreadsheetId=binance_bot_sheet_id,
                                range=from_currency+'Main!B3').execute()
    coin_risk = result_input.get('values', [])

    if not result_input and not values_expansion:
        print('No data found.')

    return float(coin_risk[0][0])

schedule.every().day.at("06:00").do(update_sheet_job, service)
schedule.every().day.at("07:00").do(send_daily_email)
update_sheet_job(service)
risk_tiers = [
    {
        'tier': '1',
        'equation': 0.00000285 * pow(math.e, 15.5*x),
        'mpa': 0.01,
        'lowest_buying_risk': 0.1,
        'next_buying_risk': 0.0,
        'next_selling_risk': 0.0,
        'coins': ['ATOM', 'XTZ']
    },
    {
        'tier': '5',
        'equation': 0.0000699 * pow(math.e, 9.8*x),
        'mpa': 0.05,
        'lowest_buying_risk': 0.225,
        'next_buying_risk': 0.0,
        'next_selling_risk': 0.0,
        'coins': ['LINK', 'ADA', 'VET', 'EOS', 'TRX']
    },
    {
        'tier': '6',
        'equation': 0.000197 * pow(math.e, 8.2*x),
        'mpa': 0.1,
        'lowest_buying_risk': 0.3,
        'next_buying_risk': 0.0,
        'next_selling_risk': 0.0,
        'coins': ['NEO']
    },
    {
        'tier': '7',
        'equation': 0.000617 * pow(math.e, 6.04*x),
        'mpa': 0.125,
        'lowest_buying_risk': 0.35,
        'next_buying_risk': 0.0,
        'next_selling_risk': 0.0,
        'coins': ['ETH', 'DASH']
    },
    {
        'tier': '8',
        'equation': 0.00128 * pow(math.e, 5.03*x),
        'mpa': 0.15,
        'lowest_buying_risk': 0.4,
        'next_buying_risk': 0.0,
        'next_selling_risk': 0.0,
        'coins': ['LTC']
    },
    {
        'tier': '9',
        'equation': 0.00281 * pow(math.e, 3.74*x),
        'mpa': 0.23,
        'lowest_buying_risk': 0.5,
        'next_buying_risk': 0.0,
        'next_selling_risk': 0.0,
        'coins': ['BTC']
    }
]
while True:
    schedule.run_pending()
    for tier in tiers:
        lowest_risked_coin = tier.get('coins')[0]
        lowest_risk = 0.00
        for coin in tier.get('coins'):
            current_risk = get_current_risks(coin, 'USD')
            if current_risk < lowest_risked_coin:
                lowest_risked_coin = coin
                lowest_risk = current_risk
        if lowest_risked < tier.get('lowest_buying_risk'):
            buy_order(lowest_risked_coin, 'USDT', tier.get('equation'), tier.get('mpa'), lowest_risk)
            tier.get('next_buying_risk') -= 0.025
    
    print(current_price)
    if risk_cool_off_btc_value - current_btc_risk >= 0.05:
        risk_cool_off_btc_value -= 0.025
    print('Current BTC risk: {}'.format(current_btc_risk))
    if current_btc_risk >= risk_cool_off_btc_value:
        risk_cool_off_btc_value = sell_order(current_btc_risk, current_price, 'BTC', 'USDT', risk_cool_off_btc_value)
    if current_btc_risk <= 0.5:
        buy_order()
    current_eth_risk = get_current_risks('ETH', 'USD')
    print(current_price)
    if risk_cool_off_eth_value - current_eth_risk >= 0.05:
        risk_cool_off_eth_value -= 0.025
    print('Current ETH risk: {}'.format(current_eth_risk))
    if current_eth_risk >= risk_cool_off_eth_value:
        risk_cool_off_eth_value = sell_order(current_eth_risk, current_price, 'ETH', 'USDT', risk_cool_off_eth_value)
    print('----------------------------')
    # I think the alpha api gets updated every minute so I'll probably change this
    time.sleep(60.0 - ((time.time() - starttime) % 60.0))