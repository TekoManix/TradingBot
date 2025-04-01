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

# ✅ Initialize Alpaca API
api = tradeapi.REST(APCA_API_KEY_ID, APCA_API_SECRET_KEY, APCA_BASE_URL, api_version="v2")

# ✅ Trading parameters
SYMBOL = "SPY"
ORDER_SIZE_PERCENT = 0.05  # Uses 5% of cash balance for each trade
TRAILING_STOP_PERCENT = 2.0  # Default 2% trailing stop
DYNAMIC_STOP_MIN = 1.0  # Minimum stop-loss percentage
DYNAMIC_STOP_MAX = 3.0  # Maximum stop-loss percentage

# ✅ Market hours check (9:30 AM - 3:55 PM EST)
nyc = pytz.timezone("America/New_York")

def is_market_open():
    now = datetime.now(nyc)
    return 9 <= now.hour < 16 or (now.hour == 9 and now.minute >= 30)

# ✅ Main trading loop
while is_market_open():
    try:
        print("\n🔄 Fetching market data...")
        # ✅ Fetch market data (1-minute timeframe)
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

        # ✅ Trend-Based Stop-Loss Adjustment
        trailing_stop = DYNAMIC_STOP_MAX if sma_50 > sma_200 else DYNAMIC_STOP_MIN

        # ✅ Buy Logic (Only Buy in Uptrend)
        if last_price < vwap and rsi < 30 and sma_50 > sma_200 and position_qty == 0:
            print(f"✅ Placing Buy Order for {order_size} shares at {last_price:.2f}...")

            order = api.submit_order(
                symbol=SYMBOL,
                qty=order_size,
                side="buy",
                type="market",
                time_in_force="gtc"
            )
            print(f"🟢 Buy order placed: {order}")

            # ✅ Apply Trailing Stop
            trailing_stop_order = api.submit_order(
                symbol=SYMBOL,
                qty=order_size,
                side="sell",
                type="trailing_stop",
                trail_percent=str(trailing_stop),
                time_in_force="gtc"
            )
            print(f"📉 Trailing stop set at {trailing_stop}% for {SYMBOL}: {trailing_stop_order}")

        # ✅ Sell Logic (Only Sell in Downtrend)
        elif last_price > vwap and rsi > 70 and sma_50 < sma_200 and position_qty > 0:
            print(f"✅ Placing Sell Order for {position_qty} shares at {last_price:.2f}...")

            order = api.submit_order(
                symbol=SYMBOL,
                qty=position_qty,
                side="sell",
                type="market",
                time_in_force="gtc"
            )
            print(f"🔴 Sell order placed: {order}")

        # ✅ Print Open Orders
        open_orders = api.list_orders(status="open")
        if open_orders:
            print("📌 Open Orders:")
            for o in open_orders:
                print(f" - {o.side.upper()} {o.qty} {o.symbol} @ {o.limit_price or 'Market'} (Status: {o.status})")

        time.sleep(60)  # ✅ Run every minute

    except tradeapi.rest.APIError as e:
        print(f"❌ APIError: {str(e)}")
    except Exception as e:
        print(f"⚠️ Unexpected error: {str(e)}")

print("❌ Market closed. Stopping bot.")
