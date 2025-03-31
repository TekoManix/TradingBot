import os
import alpaca_trade_api as tradeapi
import numpy as np
import time
import pytz
import logging
from datetime import datetime
from dotenv import load_dotenv
from alpaca_trade_api.rest import TimeFrame  

# Set up logging to both file and console
logger = logging.getLogger()
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("trading_bot.log")
stream_handler = logging.StreamHandler()

formatter = logging.Formatter("%(asctime)s - %(message)s")
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

logging.info("Bot started.")

# Load environment variables
load_dotenv()

APCA_API_KEY_ID = os.getenv('APCA_API_KEY_ID')
APCA_API_SECRET_KEY = os.getenv('APCA_API_SECRET_KEY')
APCA_BASE_URL = os.getenv('APCA_BASE_URL')

api = tradeapi.REST(APCA_API_KEY_ID, APCA_API_SECRET_KEY, APCA_BASE_URL, api_version="v2")

# Validate connection
try:
    account = api.get_account()
    logging.info(f"✅ Connected to Alpaca. Status: {account.status}")
except Exception as e:
    logging.error(f"❌ Connection error: {e}")
    exit()

symb = "SPY"
stop_loss_percent = 0.02  # 2% stop loss
take_profit_percent = 0.03  # 3% take profit

nyc = pytz.timezone("America/New_York")

while True:
    now = datetime.now(nyc)

    # ✅ Restrict trading to market hours (9:30 AM - 3:55 PM EST)
    if now.hour < 9 or (now.hour == 9 and now.minute < 30) or now.hour >= 16:
        logging.warning("❌ Market is closed. Exiting.")
        break

    # ✅ Close all positions at 3:55 PM EST
    if now.hour == 15 and now.minute >= 55:
        try:
            position = api.get_position(symb)
            qty = int(position.qty)
            if qty > 0:
                logging.info(f"📉 Closing all positions before market close...")
                api.submit_order(symbol=symb, qty=qty, side="sell", type="market", time_in_force="gtc")
                logging.info("✅ All positions closed successfully.")
        except tradeapi.rest.APIError:
            logging.info("✅ No open position to close.")
        break

    try:
        market_data = api.get_bars(symb, TimeFrame.Minute, limit=50).df

        if market_data.empty:
            logging.warning("⚠️ No market data retrieved. Skipping iteration.")
            time.sleep(60)
            continue

        market_data['vwap'] = (market_data['close'] * market_data['volume']).cumsum() / market_data['volume'].cumsum()

        close_prices = market_data['close'].values
        delta = np.diff(close_prices)
        gain = np.maximum(delta, 0)
        loss = np.abs(np.minimum(delta, 0))

        avg_gain = np.convolve(gain, np.ones(14) / 14, mode='valid')
        avg_loss = np.convolve(loss, np.ones(14) / 14, mode='valid')

        rs = avg_gain[-1] / avg_loss[-1] if avg_loss[-1] != 0 else 100
        rsi = 100 - (100 / (1 + rs))

        last_price = market_data['close'].iloc[-1]
        vwap = market_data['vwap'].iloc[-1]

        logging.info(f"📊 Last Price: {last_price:.2f}, VWAP: {vwap:.2f}, RSI: {rsi:.2f}")

        position_qty = 0
        avg_entry_price = 0
        try:
            position = api.get_position(symb)
            position_qty = int(position.qty)
            avg_entry_price = float(position.avg_entry_price)
        except tradeapi.rest.APIError:
            pass

        account = api.get_account()
        balance = float(account.cash)
        order_size = max(1, int(balance * 0.05 / last_price))

        # ✅ Buy logic
        if last_price < vwap and rsi < 30 and position_qty == 0:
            logging.info(f"✅ Placing Buy Order for {order_size} shares at {last_price:.2f}.")
            api.submit_order(symbol=symb, qty=order_size, side="buy", type="market", time_in_force="gtc")

        # ✅ Sell logic
        elif last_price > vwap and rsi > 70 and position_qty > 0:
            logging.info(f"✅ Placing Sell Order for {order_size} shares at {last_price:.2f}.")
            api.submit_order(symbol=symb, qty=order_size, side="sell", type="market", time_in_force="gtc")

        # ✅ Stop-loss & Take-profit
        if position_qty > 0:
            stop_loss_price = avg_entry_price * (1 - stop_loss_percent)
            take_profit_price = avg_entry_price * (1 + take_profit_percent)

            if last_price <= stop_loss_price:
                logging.info(f"❌ Stop loss triggered at {last_price:.2f}. Selling {position_qty} shares.")
                api.submit_order(symbol=symb, qty=position_qty, side="sell", type="market", time_in_force="gtc")

            elif last_price >= take_profit_price:
                logging.info(f"✅ Take profit triggered at {last_price:.2f}. Selling {position_qty} shares.")
                api.submit_order(symbol=symb, qty=position_qty, side="sell", type="market", time_in_force="gtc")

        time.sleep(60)

    except tradeapi.rest.APIError as e:
        logging.error(f"❌ APIError: {str(e)}")
    except Exception as e:
        logging.error(f"⚠️ Unexpected error: {str(e)}")
