import os
import os.path
import pickle
from dotenv import load_dotenv
from datetime import date

load_dotenv()
risk_strategy_sheet_id = os.getenv("RISK_STRATEGY_SHEET_ID")
binance_bot_sheet_id = os.getenv('BINANCE_BOT_SHEET_ID')

def update_sheet_job(service):

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
        spreadsheetId=binance_bot_sheet_id, range='BTCMain!A1:E',
        valueInputOption='USER_ENTERED', body=body).execute()
    print('{0} cells updated.'.format(result.get('updatedCells')))
    print('Job complete')