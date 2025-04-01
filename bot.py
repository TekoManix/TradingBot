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

# Get API keys from environment
APCA_API_KEY_ID = os.getenv('APCA_API_KEY_ID')
APCA_API_SECRET_KEY = os.getenv('APCA_API_SECRET_KEY')
APCA_BASE_URL = os.getenv('APCA_BASE_URL')

# Initialize the Alpaca API
api = tradeapi.REST(APCA_API_KEY_ID, APCA_API_SECRET_KEY, APCA_BASE_URL, api_version="v2")

symb = "SPY"
stop_loss_percent = 0.02  # 2% stop loss
take_profit_percent = 0.03  # 3% take profit

def is_market_open():
    """Check if the market is open."""
    nyc = pytz.timezone("America/New_York")
    now = datetime.now(nyc)
    return 9 <= now.hour < 16  # Market hours: 9:30 AM - 3:55 PM ET

while is_market_open():
    try:
        # ✅ Fetch market data
        market_data = api.get_bars(symb, TimeFrame.Minute, limit=50).df

        if market_data.empty:
            print("⚠️ No market data retrieved. Retrying...")
            time.sleep(30)
            continue

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

        # ✅ Calculate order size (5% of cash balance)
        account = api.get_account()
        balance = float(account.cash)
        order_size = max(1, int(balance * 0.05 / last_price))

        # ✅ Buy logic + Immediate Sell Order
        if last_price < vwap and rsi < 30 and position_qty == 0:
            print(f"✅ Placing Buy Order for {order_size} shares.")
            buy_order = api.submit_order(
                symbol=symb,
                qty=order_size,
                side="buy",
                type="market",
                time_in_force="gtc"
            )
            print(f"✅ Buy order placed at {last_price}.")

            # Wait for the order to fill before placing a sell order
            time.sleep(2)
            position = api.get_position(symb)
            avg_entry_price = float(position.avg_entry_price)

            # ✅ Set take profit & stop loss orders
            take_profit_price = avg_entry_price * (1 + take_profit_percent)
            stop_loss_price = avg_entry_price * (1 - stop_loss_percent)

            print(f"📈 Setting take-profit at {take_profit_price:.2f} and stop-loss at {stop_loss_price:.2f}.")

            # ✅ Place a limit sell order for take profit
            api.submit_order(
                symbol=symb,
                qty=order_size,
                side="sell",
                type="limit",
                time_in_force="gtc",
                limit_price=take_profit_price
            )

            # ✅ Place a stop loss order
            api.submit_order(
                symbol=symb,
                qty=order_size,
                side="sell",
                type="stop",
                time_in_force="gtc",
                stop_price=stop_loss_price
            )

        # ✅ Monitor existing positions
        if position_qty > 0:
            position = api.get_position(symb)
            avg_entry_price = float(position.avg_entry_price)

            # Check if the order is still valid
            take_profit_price = avg_entry_price * (1 + take_profit_percent)
            stop_loss_price = avg_entry_price * (1 - stop_loss_percent)

            if last_price >= take_profit_price:
                print(f"✅ Take profit hit! Selling {position_qty} shares at {last_price}.")
                api.submit_order(symbol=symb, qty=position_qty, side="sell", type="market", time_in_force="gtc")

            elif last_price <= stop_loss_price:
                print(f"❌ Stop loss hit! Selling {position_qty} shares at {last_price}.")
                api.submit_order(symbol=symb, qty=position_qty, side="sell", type="market", time_in_force="gtc")

        time.sleep(30)  # Small delay between trades

    except tradeapi.rest.APIError as e:
        print(f"❌ APIError: {str(e)}")
    except Exception as e:
        print(f"⚠️ Unexpected error: {str(e)}")

print("✅ Market closed. Trading bot stopped.")
