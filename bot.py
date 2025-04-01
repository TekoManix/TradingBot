import os
import alpaca_trade_api as tradeapi
import numpy as np
import time
import pytz
from datetime import datetime
from dotenv import load_dotenv

# ✅ Load API keys
load_dotenv()
APCA_API_KEY_ID = os.getenv("APCA_API_KEY_ID")
APCA_API_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
APCA_BASE_URL = os.getenv("APCA_BASE_URL")

# ✅ Validate API keys
if not APCA_API_KEY_ID or not APCA_API_SECRET_KEY or not APCA_BASE_URL:
    print("❌ Missing API keys! Ensure they are set in GitHub Secrets or .env file.")
    exit(1)

# ✅ Initialize Alpaca API
api = tradeapi.REST(APCA_API_KEY_ID, APCA_API_SECRET_KEY, APCA_BASE_URL, api_version="v2")

# ✅ Trading parameters
SYMBOL = "SPY"
ORDER_SIZE_PERCENT = 0.05  # Uses 5% of cash balance per trade
DYNAMIC_STOP_MIN = 1.0  # Min trailing stop
DYNAMIC_STOP_MAX = 3.0  # Max trailing stop
MARKET_CLOSE_TIME = 15 * 60 + 55  # 3:55 PM EST in minutes

# ✅ Market hours check (9:30 AM - 3:55 PM EST)
nyc = pytz.timezone("America/New_York")

def is_market_open():
    now = datetime.now(nyc)
    return 9 <= now.hour < 16 or (now.hour == 9 and now.minute >= 30)

def get_market_time():
    """ Returns the current market time in minutes past midnight (EST). """
    now = datetime.now(nyc)
    return now.hour * 60 + now.minute

# ✅ Ensure positions are closed before market close
def close_all_positions():
    """ Closes all open positions before market close. """
    positions = api.list_positions()
    for position in positions:
        symbol = position.symbol
        qty = abs(int(position.qty))  # Ensure quantity is positive
        print(f"⚠️ Closing {qty} shares of {symbol} before market close.")
        api.submit_order(
            symbol=symbol,
            qty=qty,
            side="sell",
            type="market",
            time_in_force="gtc"
        )

# ✅ Main trading loop
while is_market_open():
    try:
        if get_market_time() >= MARKET_CLOSE_TIME:
            print("🚨 Market is closing soon. Closing all positions...")
            close_all_positions()
            break  # Stop trading loop

        print("\n🔄 Fetching market data...")
        market_data = api.get_bars(SYMBOL, tradeapi.TimeFrame.Minute, limit=200).df  

        if market_data.empty:
            print("⚠️ No market data retrieved. Retrying in 60s...")
            time.sleep(60)
            continue

        # ✅ Compute Moving Averages
        market_data["SMA_50"] = market_data["close"].rolling(window=50).mean()
        market_data["SMA_200"] = market_data["close"].rolling(window=200).mean()

        # ✅ Compute VWAP
        market_data["vwap"] = (market_data["close"] * market_data["volume"]).cumsum() / market_data["volume"].cumsum()

        # ✅ Compute RSI
        close_prices = market_data["close"].values
        if len(close_prices) < 15:
            print("⚠️ Not enough price data for RSI calculation. Skipping...")
            time.sleep(60)
            continue

        delta = np.diff(close_prices)
        gain = np.maximum(delta, 0)
        loss = np.abs(np.minimum(delta, 0))
        avg_gain = np.convolve(gain, np.ones(14) / 14, mode="valid")
        avg_loss = np.convolve(loss, np.ones(14) / 14, mode="valid")
        rs = avg_gain[-1] / avg_loss[-1] if avg_loss[-1] != 0 else 100
        rsi = 100 - (100 / (1 + rs))

        # ✅ Get latest price, VWAP, SMA values
        last_price = market_data["close"].iloc[-1]
        vwap = market_data["vwap"].iloc[-1]
        sma_50 = market_data["SMA_50"].iloc[-1]
        sma_200 = market_data["SMA_200"].iloc[-1]

        print(f"📊 Last Price: {last_price:.2f}, VWAP: {vwap:.2f}, RSI: {rsi:.2f}")
        print(f"📈 SMA 50: {sma_50:.2f}, SMA 200: {sma_200:.2f}")

        # ✅ Get account balance & position
        account = api.get_account()
        balance = float(account.cash)
        print(f"💰 Available Cash: {balance:.2f}")

        position_qty = 0
        try:
            position = api.get_position(SYMBOL)
            position_qty = int(position.qty)
            print(f"📊 Current Position: {position_qty} shares")
        except tradeapi.rest.APIError:
            print("ℹ️ No open positions.")

        # ✅ Calculate order size (5% of cash balance)
        order_size = max(1, int(balance * ORDER_SIZE_PERCENT / last_price))
        print(f"📌 Order Size: {order_size} shares")

        # ✅ Buy Logic
        if last_price < vwap and rsi < 30 and sma_50 > sma_200 and position_qty == 0:
            print(f"✅ Placing Buy Order for {order_size} shares at {last_price:.2f}...")

            api.submit_order(
                symbol=SYMBOL,
                qty=order_size,
                side="buy",
                type="market",
                time_in_force="gtc"
            )

        # ✅ Sell Logic
        elif last_price > vwap and rsi > 70 and sma_50 < sma_200 and position_qty > 0:
            print(f"✅ Placing Sell Order for {position_qty} shares at {last_price:.2f}...")

            api.submit_order(
                symbol=SYMBOL,
                qty=position_qty,
                side="sell",
                type="market",
                time_in_force="gtc"
            )

        time.sleep(60)  # ✅ Run every minute

    except tradeapi.rest.APIError as e:
        print(f"❌ APIError: {str(e)}")
    except Exception as e:
        print(f"⚠️ Unexpected error: {str(e)}")

print("❌ Market closed. Stopping bot.")
