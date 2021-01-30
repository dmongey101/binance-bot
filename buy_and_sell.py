import os
import math
from binance.client import Client
from binance.enums import *
from geminipy import Geminipy
from dotenv import load_dotenv

load_dotenv()

# api_key = os.getenv("BINANCE_API_KEY")
# api_secret = os.getenv("BINANCE_API_SECRET")
# client = Client(api_key, api_secret)

api_key = os.getenv("GEMINI_SANDBOX_API_KEY")
api_secret = os.getenv("GEMINI_SANDBOX_API_SECRET")

con = Geminipy(api_key=api_key, secret_key=api_secret)

def sell_order(current_btc_risk, current_price, from_currency, to_currency, risk_cool_off_value):
    # this needs to be the initial amount of btc
    btc_holding = float(client.get_asset_balance(asset=from_currency).get('free'))
    slo_div = 0.0753 + 0.0897*math.log(current_btc_risk)
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
    
def buy_order(from_currency, to_currency, mpa, current_risk, tier, current_price):
    total_portfolio_balance = get_total_account_balance_gemini(current_price)
    from_currency_balance = get_balance(from_currency, True)
    print('Total value of {0} is {1} USD'.format(from_currency, from_currency_balance))
    to_currency_balance = get_balance(to_currency)
    print('Total value of {0} is {1}'.format(to_currency, to_currency_balance))
    percentage_of_portfolio = from_currency_balance/total_portfolio_balance
    if percentage_of_portfolio > mpa:
        print('Max portfolio allocation limit reached')
    else:
        amount_to_buy = 0.0
        if tier == '1':
            amount_to_buy = 0.00000285 * pow(math.e, 15.5*current_risk)
        if tier == '5':
            amount_to_buy = 0.0000699 * pow(math.e, 9.8*current_risk)
        if tier == '6':
            amount_to_buy = 0.000197 * pow(math.e, 8.2*current_risk)
        if tier == '7':
            amount_to_buy = 0.000617 * pow(math.e, 6.04*current_risk)
        if tier == '8':
            amount_to_buy = 0.00128 * pow(math.e, 5.03*current_risk)
        if tier == '9':
            amount_to_buy = 0.00281 * pow(math.e, 3.74*current_risk)
        print(amount_to_buy)
        order_amount = (total_portfolio_balance * mpa) * amount_to_buy

        if order_amount > to_currency_balance:
            order_amount = to_currency_balance

        order_amount = float(format(order_amount/current_price, ".5f"))
        print('Attempting to buy {0} {1}'.format(order_amount, from_currency))
        # for testing only
        try:
            order = con.new_order(
                amount=str(order_amount-100),
                price=str(current_price),
                side='buy',
                symbol=from_currency+to_currency,
                options=['immediate-or-cancel']
            )
            print(order.json())
        except:
            print('Order failed')
            pass    
        # for production only
        # order = client.order_market_buy(
        #     symbol=from_currency+to_currency,
        #     quantity=order_amount)


def get_total_account_balance_binance():
    print('Calculating total USDT balance')
    total_usdt_balance = 0.0
    balances = client.get_account().get('balances')
    for price in balances:
        if price.get('free') not in ['0.00000000', '0.00'] and price.get('asset') not in ['BUSD', 'USDT']:
            coin = price.get('asset')
            avg_price = client.get_avg_price(symbol=coin+'USDT')
            total_usdt_balance += float(avg_price.get('price')) * float(price.get('free'))
        if price.get('asset') == 'USDT':
            total_usdt_balance += float(price.get('free'))
    return total_usdt_balance

def get_total_account_balance_gemini(current_price):
    print('Calculating total USD balance')
    total_usd_balance = 0.0
    balances = con.notionalBalances().json()
    for coin in balances:
        total_usd_balance += float(coin.get('availableNotional'))
    print('Total balance is {}'.format(total_usd_balance))
    return total_usd_balance

def get_balance(currency, notional=False):
    if notional:
        balances = con.notionalBalances().json()
        for balance in balances:
            if balance.get('currency') == currency:
                return float(balance.get('availableNotional'))
    else:
        balances = con.balances().json()
        for balance in balances:
            if balance.get('currency') == currency:
                return float(balance.get('available'))
    return 0.0

