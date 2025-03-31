import os
import alpaca_trade_api as tradeapi
import numpy as np
import time
from dotenv import load_dotenv
from alpaca_trade_api.rest import TimeFrame  

# Load environment variables
load_dotenv()

# Get API keys from the environment
APCA_API_KEY_ID = os.getenv('APCA_API_KEY_ID')
APCA_API_SECRET_KEY = os.getenv('APCA_API_SECRET_KEY')
APCA_BASE_URL = os.getenv('APCA_BASE_URL')

# Initialize the Alpaca API
api = tradeapi.REST(APCA_API_KEY_ID, APCA_API_SECRET_KEY, APCA_BASE_URL, api_version="v2")

try:
    account = api.get_account()
    print("✅ Successfully connected to Alpaca!")
    print(f"Account status: {account.status}")
    print(f"Cash Balance: ${account.cash}")
except Exception as e:
    print(f"❌ Connection error: {e}")
    exit()

symb = "SPY"
hours_to_test = 2

# ✅ Check if market is open
clock = api.get_clock()
if not clock.is_open:
    print("⚠️ Market is currently closed. No data available.")
    exit()

print("✅ Checking Price...")

try:
    # ✅ Fetch market data
    market_data = api.get_bars(symb, TimeFrame.Minute, limit=(60 * hours_to_test)).df  

    # ✅ Debug: Print received data
    print("📊 Market Data Retrieved:\n", market_data.head())

    # ✅ Ensure the data is not empty
    if market_data.empty:
        print("⚠️ Warning: No market data retrieved. Check symbol, market hours, or API keys.")
        exit()

    close_list = market_data['close'].values  

    print(f"📈 Open Price: {close_list[0]}")
    print(f"📉 Close Price: {close_list[-1]}")

    close_list = np.array(close_list, dtype=np.float64)

    buys = 0
    sells = 0

    # ✅ Start at index 4 for moving average calculation
    for i in range(4, len(close_list)):
        ma = np.mean(close_list[i-4:i+1])
        last_price = close_list[i]

        print(f"📊 Moving Average: {ma:.2f}, Last Price: {last_price:.2f}")

        # ✅ Check current position
        position_qty = 0
        try:
            position = api.get_position(symb)
            position_qty = int(position.qty)
        except tradeapi.rest.APIError:
            # No position currently held
            pass

        # ✅ Buy logic
        if ma + 0.1 < last_price and position_qty == 0:
            print("✅ Placing Buy Order")
            order = api.submit_order(
                symbol=symb,
                qty=10,  # Buying 1 share
                side="buy",
                type="market",
                time_in_force="gtc"
            )
            buys += 1

        # ✅ Sell logic
        elif ma - 0.1 > last_price and position_qty > 0:
            print("✅ Placing Sell Order")
            order = api.submit_order(
                symbol=symb,
                qty=1,  # Selling 1 share
                side="sell",
                type="market",
                time_in_force="gtc"
            )
            sells += 1

        # ✅ Print current position
        try:
            position = api.get_position(symb)
            print(f"💰 Current Position: {position.qty} shares")
        except tradeapi.rest.APIError:
            print(f"💰 No open position in {symb}")

        time.sleep(1)  # Small delay between trades

    print("\n📊 Trade Summary")
    print(f"💸 Total Buys: {buys}")
    print(f"💰 Total Sells: {sells}")

except tradeapi.rest.APIError as e:
    print("❌ APIError:", str(e))
except Exception as e:
    print("⚠️ Unexpected error:", str(e))
