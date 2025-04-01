import os
import alpaca_trade_api as tradeapi
import numpy as np
import time
import pytz
from datetime import datetime
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

# Validate connection
try:
    account = api.get_account()
    print("✅ Successfully connected to Alpaca!")
    print(f"Account status: {account.status}")
    print(f"Cash Balance: ${account.cash}")
except Exception as e:
    print(f"❌ Connection error: {e}")
    exit()

symb = "SPY"

# ✅ Restrict trading to market hours (9:30 AM - 3:55 PM EST)
nyc = pytz.timezone("America/New_York")
now = datetime.now(nyc)

if now.hour < 9 or (now.hour == 9 and now.minute < 30) or now.hour >= 16:
    print("❌ Market is closed. Exiting.")
    exit()

# ✅ Close all positions at 3:55 PM EST
if now.hour == 15 and now.minute >= 55:
    try:
        position = api.get_position(symb)
        qty = int(position.qty)
        if qty > 0:
            print("📉 Closing all positions before market close...")
            api.submit_order(symbol=symb, qty=qty, side="sell", type="market", time_in_force="gtc")
    except tradeapi.rest.APIError:
        print("✅ No open position to close.")
    exit()

# ✅ Fetch latest market data (1-minute timeframe)
try:
    market_data = api.get_bars(symb, TimeFrame.Minute, limit=50).df

    if market_data.empty:
        print("⚠️ No market data retrieved. Exiting.")
        exit()

    # ✅ Compute VWAP
    market_data['vwap'] = (market_data['close'] * market_data['volume']).cumsum() / market_data['volume'].cumsum()

    # ✅ Compute RSI
    close_prices = market_data['close'].values
    delta = np.diff(close_prices)
    gain = np.maximum(delta, 0)
    loss = np.abs(np.minimum(delta, 0))

    avg_gain = np.convolve(gain, np.ones(14) / 14, mode='valid')
    avg_loss = np.convolve(loss, np.ones(14) / 14, mode='valid')

    rs = avg_gain[-1] / avg_loss[-1] if avg_loss[-1] != 0 else 100
    rsi = 100 - (100 / (1 + rs))

    # ✅ Get latest price, VWAP, and RSI
    last_price = market_data['close'].iloc[-1]
    vwap = market_data['vwap'].iloc[-1]

    print(f"📊 Last Price: {last_price:.2f}, VWAP: {vwap:.2f}, RSI: {rsi:.2f}")

    # ✅ Get current position
    position_qty = 0
    try:
        position = api.get_position(symb)
        position_qty = int(position.qty)
    except tradeapi.rest.APIError:
        pass  # No open position

    # ✅ Calculate dynamic order size (5% of cash balance)
    account = api.get_account()
    balance = float(account.cash)
    order_size = max(1, int(balance * 0.05 / last_price))

    # ✅ Buy logic (VWAP & RSI strategy)
    if last_price < vwap and rsi < 30 and position_qty == 0:
        print("✅ Placing Buy Order")
        api.submit_order(symbol=symb, qty=order_size, side="buy", type="market", time_in_force="gtc")

    # ✅ Sell logic (VWAP & RSI strategy)
    elif last_price > vwap and rsi > 70 and position_qty > 0:
        print("✅ Placing Sell Order")
        api.submit_order(symbol=symb, qty=order_size, side="sell", type="market", time_in_force="gtc")

    time.sleep(1)  # Small delay between trades

except tradeapi.rest.APIError as e:
    print("❌ APIError:", str(e))
except Exception as e:
    print("⚠️ Unexpected error:", str(e))