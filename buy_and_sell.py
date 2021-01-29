import os
import math
from binance.client import Client
from binance.enums import *
from geminipy import Geminipy

api_key = os.getenv("GEMINI_API_KEY")
api_secret = os.getenv("GEMINI_API_SECRET")

con = Geminipy(api_key=api_key, secret_key=api_secret, live=True)
symbols = con.symbols()
print(symbols.json())
# api_key = os.getenv("BINANCE_API_KEY")
# api_secret = os.getenv("BINANCE_API_SECRET")
# client = Client(api_key, api_secret)
# client.API_URL = 'https://testnet.binance.vision/api'


risk_tiers = [
    'tier1': ['ATOM', 'XTZ'],
    'tier5': ['LINK', 'ADA', 'VET', 'EOS', 'TRX'],
    'tier6': ['NEO'],
    'tier7': ['ETH', 'DASH'],
    'tier8': ['LTC'],
    'tier9': ['BTC']
]

def sell_order(current_btc_risk, current_price, from_currency, to_currency, risk_cool_off_value):
    # this needs to be the initial amount of btc
    btc_holding = float(client.get_asset_balance(asset=from_currency).get('free'))
    slo_div = 0.0753 + 0.0897*math.log(current_btc_risk)
    2.81E-03e^3.74x
    slo_btc_amount = float(format(btc_holding * slo_div, ".5f"))
    slo_price = math.floor(current_price-500)
    print('Looking for previous orders')
    old_order = client.get_open_orders(symbol=from_currency+to_currency)
    if old_order:
        old_order_id = old_order[0].get('orderId')
        print('Order found with id {}'.format(old_order_id))
        result = client.cancel_order(
            symbol=from_currency+to_currency,
            orderId=str(old_order_id)
        )
        print('Cancelled order with id {}'.format(old_order_id))
    else:
        print('No order found')
    print('Creating new order')
    print('Quantity: {0} {1}'.format(slo_btc_amount, from_currency))
    print('Sell Price: ${}'.format(slo_price))
    new_order = client.create_order(
        symbol=from_currency+to_currency,
        side=SIDE_SELL,
        type=ORDER_TYPE_LIMIT,
        timeInForce=TIME_IN_FORCE_GTC,
        quantity=slo_btc_amount,
        price=slo_price
    )
    print('Sell order created')
    risk_cool_off_value += 0.025
    risk_cool_off_value = round(risk_cool_off_value, 3)
    print('New sell order risk is set to {}'.format(risk_cool_off_value))
    return risk_cool_off_value
    
    
def buy_order(from_currency, to_currency, equation, mpa, current_risk):
    to_currency_balance = client.get_asset_balance(asset=to_currency)
    print('Your {0} balance was {1} {2}'.format(to_currency, to_currency_balance.get('free')), to_currency)
    x = current_risk
    amount_to_buy = equation
    print(amount_to_buy)
    order = client.order_market_buy(
        symbol=from_currency+to_currency,
        quantity=amount_to_buy)
    print(order)
    to_currency_balance = client.get_asset_balance(asset=to_currency)
    print('Your {0} balance is now {1} {2}'.format(to_currency, to_currency_balance.get('free')), to_currency)
    print('You bought 0.3 ' + from_currency)
    from_currency_balance = client.get_asset_balance(asset=from_currency)
    print('Your {0} balance is now {1} {2}'.format(from_currency, from_currency_balance.get('free'), from_currency))
    global risk_cool_off_value
    risk_cool_off_value += 0.025
    risk_cool_off_value = round(risk_cool_off_value, 3)
    print('New sell order risk is set to {}'.format(risk_cool_off_value))