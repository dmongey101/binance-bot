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
    if response.get('Realtime Currency Exchange Rate') is None:
        print('Alpha api limit exceeded. Cooling off for 30 seconds')
        time.sleep(30.0 - ((time.time() - starttime) % 30.0))
    return response

def get_current_risks(from_currency, to_currency):
    global current_price
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
schedule.every().day.at("06:10").do(send_daily_email)

risk_tiers = [
    # {
    #     'tier': '1',
    #     'mpa': 0.01,
    #     'lowest_buying_risk': 0.1,
    #     'coins': [
    #         {
    #             'coin': 'ATOM',
    #             'next_sell_risk': 0.525
    #         },
    #         {
    #             'coin': 'XTZ',
    #             'next_sell_risk': 0.525
    #         }
    #     ]
    # },
    {
        'tier': '5',
        'mpa': 0.05,
        'lowest_buying_risk': 0.225,
        'coins': [
            {
                'coin': 'LINK',
                'next_sell_risk': 0.525
            },
            # {
            #     'coin': 'ADA',
            #     'next_sell_risk': 0.525
            # },
            # {
            #     'coin': 'VET',
            #     'next_sell_risk': 0.525
            # },
            # {
            #     'coin': 'EOS',
            #     'next_sell_risk': 0.525
            # },
            # {
            #     'coin': 'TRX',
            #     'next_sell_risk': 0.525
            # }
        ]
    },
    # {
    #     'tier': '6',
    #     'mpa': 0.1,
    #     'lowest_buying_risk': 0.3,
    #     'coins': [
    #         {
    #             'coin': 'NEO',
    #             'next_sell_risk': 0.525
    #         }
    #     ]
    # },
    {
        'tier': '7',
        'mpa': 0.125,
        'lowest_buying_risk': 0.35,
        'coins': [
            {
                'coin': 'ETH',
                'next_sell_risk': 0.525
            },
            # {
            #     'coin': 'DASH',
            #     'next_sell_risk': 0.525
            # }
        ]
    },
    {
        'tier': '8',
        'mpa': 0.15,
        'lowest_buying_risk': 0.4,
        'coins': [
            {
                'coin': 'LTC',
                'next_sell_risk': 0.525
            }
        ]
    },
    {
        'tier': '9',
        'mpa': 0.23,
        'lowest_buying_risk': 0.5,
        'coins': [
            {
                'coin': 'BTC',
                'next_sell_risk': 0.525
            }
        ]
    }
]
while True:
    schedule.run_pending()
    for tier in risk_tiers:
        for coin in tier.get('coins'):
            current_risk = get_current_risks(coin.get('coin'), 'USD')
            print('Current {0} is {1}'.format(coin.get('coin'), current_risk))
            if current_risk < tier.get('lowest_buying_risk'):
                buy_order(coin.get('coin'), 'USD', tier.get('mpa'), current_risk, tier.get('tier'), current_price)
                # coin.get('next_sell_risk') = 0.525
    # print(current_price)
    # if risk_cool_off_btc_value - current_btc_risk >= 0.05:
    #     risk_cool_off_btc_value -= 0.025
    # print('Current BTC risk: {}'.format(current_btc_risk))
    # if current_btc_risk >= risk_cool_off_btc_value:
    #     risk_cool_off_btc_value = sell_order(current_btc_risk, current_price, 'BTC', 'USDT', risk_cool_off_btc_value)
    # if current_btc_risk <= 0.5:
    #     buy_order()
    # current_eth_risk = get_current_risks('ETH', 'USD')
    # print(current_price)
    # if risk_cool_off_eth_value - current_eth_risk >= 0.05:
    #     risk_cool_off_eth_value -= 0.025
    # print('Current ETH risk: {}'.format(current_eth_risk))
    # if current_eth_risk >= risk_cool_off_eth_value:
    #     risk_cool_off_eth_value = sell_order(current_eth_risk, current_price, 'ETH', 'USDT', risk_cool_off_eth_value)
    print('----------------------------')
    time.sleep(60.0 - ((time.time() - starttime) % 60.0))