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

# Create a file handler and set level to INFO
file_handler = logging.FileHandler("trading_bot.log")
file_handler.setLevel(logging.INFO)

# Create a stream handler to log to console
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)

# Define log format
formatter = logging.Formatter("%(asctime)s - %(message)s")
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# Add both handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Log initial message
logging.info("Bot started.")

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
    logging.info(f"✅ Successfully connected to Alpaca!")
    logging.info(f"Account status: {account.status}")
    logging.info(f"Cash Balance: ${account.cash}")
except Exception as e:
    logging.error(f"❌ Connection error: {e}")
    exit()

symb = "SPY"
stop_loss_percent = 0.02  # 2% stop loss
take_profit_percent = 0.03  # 3% take profit

# ✅ Restrict trading to market hours (9:30 AM - 3:55 PM EST)
nyc = pytz.timezone("America/New_York")
now = datetime.now(nyc)

if now.hour < 9 or (now.hour == 9 and now.minute < 30) or now.hour >= 16:
    logging.warning("❌ Market is closed. Exiting.")
    exit()

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
    exit()

# ✅ Fetch latest market data (1-minute timeframe)
try:
    market_data = api.get_bars(symb, TimeFrame.Minute, limit=50).df

    if market_data.empty:
        logging.warning("⚠️ No market data retrieved. Exiting.")
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

    logging.info(f"📊 Last Price: {last_price:.2f}, VWAP: {vwap:.2f}, RSI: {rsi:.2f}")

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
        logging.info(f"✅ Placing Buy Order for {order_size} shares.")
        api.submit_order(symbol=symb, qty=order_size, side="buy", type="market", time_in_force="gtc")
        logging.info(f"✅ Buy order placed at {last_price}.")

    # ✅ Sell logic (VWAP & RSI strategy)
    elif last_price > vwap and rsi > 70 and position_qty > 0:
        logging.info(f"✅ Placing Sell Order for {order_size} shares.")
        api.submit_order(symbol=symb, qty=order_size, side="sell", type="market", time_in_force="gtc")
        logging.info(f"✅ Sell order placed at {last_price}.")

    # ✅ Implement stop loss and take profit
    if position_qty > 0:
        avg_entry_price = float(position.avg_entry_price)

        # Stop loss logic
        stop_loss_price = avg_entry_price * (1 - stop_loss_percent)
        if last_price <= stop_loss_price:
            logging.info(f"❌ Stop loss triggered. Selling {position_qty} shares at {last_price}.")
            api.submit_order(symbol=symb, qty=position_qty, side="sell", type="market", time_in_force="gtc")
            logging.info("✅ Stop loss executed.")

        # Take profit logic
        take_profit_price = avg_entry_price * (1 + take_profit_percent)
        if last_price >= take_profit_price:
            logging.info(f"✅ Take profit triggered. Selling {position_qty} shares at {last_price}.")
            api.submit_order(symbol=symb, qty=position_qty, side="sell", type="market", time_in_force="gtc")
            logging.info("✅ Take profit executed.")

    time.sleep(1)  # Small delay between trades

except tradeapi.rest.APIError as e:
    logging.error(f"❌ APIError: {str(e)}")
except Exception as e:
    logging.error(f"⚠️ Unexpected error: {str(e)}")
