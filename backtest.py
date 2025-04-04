import os
import alpaca_trade_api as tradeapi
import numpy as np
import time
from dotenv import load_dotenv
from alpaca_trade_api.rest import TimeFrame  # ✅ Correct TimeFrame import
import matplotlib.pyplot as plt

# Load environment variables
load_dotenv()

# Use the correct environment variables
ALPACA_API_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = "https://paper-api.alpaca.markets/"  # or the live API URL if applicable

# Initialize the Alpaca API
api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL)

symb = "SPY"
pos_held = False
hours_to_test = 2

# ✅ Check if market is open
clock = api.get_clock()
if not clock.is_open:
    print("⚠️ Market is currently closed. No data available.")
    exit()

print("✅ Checking Price...")

try:
    # ✅ Fetch market data using correct TimeFrame
    market_data = api.get_bars(symb, TimeFrame.Minute, limit=(60 * hours_to_test)).df  # ✅ Convert to DataFrame

    # ✅ Debug: Print received data
    print("📊 Market Data Retrieved:\n", market_data.head())

    # ✅ Ensure the data is not empty
    if market_data.empty:
        print("⚠️ Warning: No market data retrieved. Check symbol, market hours, or API keys.")
        exit()

    close_list = market_data['close'].values  # ✅ Correctly extract 'close' column

    print(f"📈 Open Price: {close_list[0]}")
    print(f"📉 Close Price: {close_list[-1]}")

    close_list = np.array(close_list, dtype=np.float64)
    startBal = 2000  # Start with $2000
    balance = startBal
    buys = 0
    sells = 0

    # ✅ Backtesting logic
    trades = []
    for i in range(4, len(close_list)):
        ma = np.mean(close_list[i-4:i+1])
        last_price = close_list[i]

        print(f"📊 Moving Average: {ma:.2f}, Last Price: {last_price:.2f}")

        # Buy signal: When the last price is greater than the moving average by a certain threshold
        if ma + 0.1 < last_price and not pos_held:
            print("✅ Buy Order Executed")
            balance -= last_price
            pos_held = True
            buys += 1
            trades.append({'action': 'buy', 'price': last_price, 'balance': balance})

        # Sell signal: When the last price is lower than the moving average by a certain threshold
        elif ma - 0.1 > last_price and pos_held:
            print("✅ Sell Order Executed")
            balance += last_price
            pos_held = False
            sells += 1
            trades.append({'action': 'sell', 'price': last_price, 'balance': balance})

        print(f"💰 Current Balance: {balance:.2f}")
        time.sleep(0.01)

    # If still holding a position at the end of the backtest, sell it
    if pos_held:
        balance += close_list[-1]
        trades.append({'action': 'sell', 'price': close_list[-1], 'balance': balance})

    print("\n📊 Trade Summary")
    print(f"💸 Total Buys: {buys}")
    print(f"💰 Total Sells: {sells}")
    print(f"🏁 Final Balance: {balance:.2f}")

    # Plot the results
    balance_over_time = [trade['balance'] for trade in trades]
    plt.plot(balance_over_time)
    plt.title('Equity Curve')
    plt.xlabel('Trade Number')
    plt.ylabel('Balance')
    plt.show()

    print(f"📈 Profit if held: {close_list[-1] - close_list[0]:.2f}")
    print(f"📊 Profit from algorithm: {balance - startBal:.2f}")

except tradeapi.rest.APIError as e:
    print("❌ APIError:", str(e))
except Exception as e:
    print("⚠️ Unexpected error:", str(e))
