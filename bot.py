import alpaca_trade_api as tradeapi
import numpy as np
import time
import os
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("BASE_URL")

api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL)

SYMBOL = "SPY"
START_BALANCE = 2000
BALANCE = START_BALANCE
TRADE_SIZE = 50
SMA_PERIOD = 50
DCA_INTERVAL = 5

print("Fetching market data...")
market_data = api.get_barset(SYMBOL, 'minute', limit=100)
close_list = np.array([bar.c for bar in market_data[SYMBOL]])

buys, sells, pos_held = 0, 0, False

for i in range(SMA_PERIOD, len(close_list)):
    sma = np.mean(close_list[i - SMA_PERIOD:i])
    last_price = close_list[i]

    if last_price < sma * 0.98 and BALANCE >= TRADE_SIZE:
        print("Buying SPY")
        BALANCE -= last_price
        pos_held = True
        buys += 1

    elif last_price > sma * 1.02 and pos_held:
        print("Selling SPY")
        BALANCE += last_price
        pos_held = False
        sells += 1

if pos_held:
    BALANCE += close_list[-1]

print(f"Final Balance: {BALANCE}")
print(f"Profit from bot: {BALANCE - START_BALANCE}")
