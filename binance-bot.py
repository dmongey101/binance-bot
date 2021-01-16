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

    # here enter the id of your google sheet
    SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
    SAMPLE_RANGE_NAME = 'BTC!A2:G'

    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

    def get_current_price(from_currency, to_currency):
        alpha_base_url = os.getenv('ALPHA_BASE_URL')
        alpha_api_key = os.getenv('ALPHA_API_KEY')
        url = alpha_base_url + 'query?function=CURRENCY_EXCHANGE_RATE&from_currency=' + from_currency + '&to_currency=' + to_currency + '&apikey=' + alpha_api_key
        response = requests.get(url).json()
        return response.get('Realtime Currency Exchange Rate', {}).get('5. Exchange Rate')

    def main():
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

        # Call the Sheets API
        sheet = service.spreadsheets()
        result_input = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                    range=SAMPLE_RANGE_NAME).execute()
        data = result_input.get('values', [])

        if not data and not values_expansion:
            print('No data found.')

        current_btc_price = get_current_price("BTC", "USD")
        data[1][0] = current_btc_price
        df = pd.DataFrame(data[1:], columns=data[0])
        
        print(df)
        
    #     return data

    def btc_sell_order(current_btc_risk):
        if current_btc_risk > 0.857:
            client.order_market_sell(
                symbol='BTCUSD',
                quantity=0.01
            )

    main()
        
        # while True:
        
        # print(btc_risk)
        # btc_sell_order(int(float(btc_risk)))
    #     time.sleep(5.0 - ((time.time() - starttime) % 5.0))

    # print(values_input)