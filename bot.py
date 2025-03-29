import os
import numpy as np
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import TimeFrame  # Correct TimeFrame Import

# Load API keys from .env
load_dotenv()
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = os.getenv("BASE_URL")

# Initialize API
api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL)

# Define Parameters
SYMBOL = "SPY"
START_BALANCE = 2000
BALANCE = START_BALANCE
TRADE_SIZE = 50
SMA_PERIOD = 50

# Fetch market data
print("Fetching market data...")
market_data = api.get_bars(SYMBOL, TimeFrame.Minute, limit=100).df  # ✅ Corrected TimeFrame

# Debugging step: print the first few rows and column names
print(market_data.head())  # Display the first few rows of data
print(market_data.columns)  # Display column names to verify

# Correctly access the 'close' column in the DataFrame
close_list = market_data['close'].values

buys, sells, pos_held = 0, 0, False

for i in range(SMA_PERIOD, len(close_list)):
    sma = np.mean(close_list[i - SMA_PERIOD:i])  # Calculate SMA
    last_price = close_list[i]  # Current market price

    # Mean Reversion Buy Logic
    if last_price < sma * 0.98 and BALANCE >= TRADE_SIZE:
        print("Buying SPY (Mean Reversion Buy)")
        BALANCE -= last_price
        pos_held = True
        buys += 1

    # Mean Reversion Sell Logic
    elif last_price > sma * 1.02 and pos_held:
        print("Selling SPY (Mean Reversion Sell)")
        BALANCE += last_price
        pos_held = False
        sells += 1

# If position is still held, sell at the last price
if pos_held:
    BALANCE += close_list[-1]

# Final Results
print(f"Final Balance: {BALANCE}")
print(f"Profit from bot: {BALANCE - START_BALANCE}")
print(f"Total Buys: {buys}, Total Sells: {sells}")
