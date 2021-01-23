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
from buy_and_sell import btc_sell_order, btc_buy_order

starttime = time.time()
load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# here enter the id of your google sheet
risk_strategy_sheet_id = os.getenv("RISK_STRATEGY_SHEET_ID")
binance_bot_sheet_id = os.getenv('BINANCE_BOT_SHEET_ID')

risk_cool_off_btc_value = 0.775
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

    btc_price_json = get_current_price(from_currency, to_currency)
    if btc_price_json is None:
        btc_price_json = get_current_price(from_currency, to_currency)
    
    current_price = float(btc_price_json.get('Realtime Currency Exchange Rate', {}).get('5. Exchange Rate'))
    current_price_time = btc_price_json.get('Realtime Currency Exchange Rate', {}).get('6. Last Refreshed')   
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
    print('{0} cell updated with price {1} at {2}'.format(result.get('updatedCells'), "{:.2f}".format(float(current_price)), current_price_time))

    # getting current risk from sheet
    sheet = service.spreadsheets()
    result_input = sheet.values().get(spreadsheetId=binance_bot_sheet_id,
                                range=from_currency+'Main!B3').execute()
    btc_risk = result_input.get('values', [])

    if not result_input and not values_expansion:
        print('No data found.')

    return float(btc_risk[0][0])

# schedule.every().monday.at("09:00").do(update_sheet_job)
schedule.every().day.at("06:00").do(update_sheet_job, service)
schedule.every().day.at("07:00").do(send_daily_email)

while True:
    schedule.run_pending()
    current_btc_risk = get_current_risks('BTC', 'USD')
    current_eth_risk = get_current_risks('ETH', 'USD')
    if risk_cool_off_btc_value - current_btc_risk >= 0.05:
        risk_cool_off_btc_value -= 0.025
    print('Current BTC risk: {}'.format(current_btc_risk))
    if current_btc_risk >= risk_cool_off_btc_value:
        risk_cool_off_btc_value = btc_sell_order(current_btc_risk, current_price, 'BTC', 'USDT', risk_cool_off_btc_value)
    if current_btc_risk <= 0.5:
        btc_buy_order()
    if risk_cool_off_eth_value - current_eth_risk >= 0.05:
        risk_cool_off_eth_value -= 0.025
    print('Current ETH risk: {}'.format(current_eth_risk))
    if current_eth_risk >= risk_cool_off_eth_value:
        risk_cool_off_eth_value = btc_sell_order(current_eth_risk, current_price, 'ETH', 'USDT', risk_cool_off_eth_value)
    print('----------------------------')
    # I think the alpha api gets updated every minute so I'll probably change this
    time.sleep(60.0 - ((time.time() - starttime) % 60.0))