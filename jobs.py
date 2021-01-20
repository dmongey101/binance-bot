import os
import os.path
import pickle
from dotenv import load_dotenv
from datetime import date
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow,Flow
from google.auth.transport.requests import Request
load_dotenv()
risk_strategy_sheet_id = os.getenv("RISK_STRATEGY_SHEET_ID")
binance_bot_sheet_id = os.getenv('BINANCE_BOT_SHEET_ID')

def update_sheet_job():
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
    print('Getting data from BTC sheet')
    result = service.spreadsheets().values().get(
        spreadsheetId=risk_strategy_sheet_id, range='BTC!A1:E').execute()
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

    body = {
        'values': current_risk_sheet
    }
    print('Updating the current sheet')
    result = service.spreadsheets().values().update(
        spreadsheetId=binance_bot_sheet_id, range='Binance-bot!A1:E',
        valueInputOption='USER_ENTERED', body=body).execute()
    print('{0} cells updated.'.format(result.get('updatedCells')))
    print('Job complete')