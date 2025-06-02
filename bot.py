import os
import alpaca_trade_api as tradeapi
import numpy as np
import pandas as pd
import time
import pytz
import logging
import sys
from datetime import datetime
from dotenv import load_dotenv
from alpaca_trade_api.rest import TimeFrame

# Set up logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def validate_environment():
    """Validate that all required environment variables are set."""
    required_vars = ['APCA_API_KEY_ID', 'APCA_API_SECRET_KEY', 'APCA_BASE_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    return True

def is_market_open():
    """Check if the market is currently open."""
    nyc = pytz.timezone("America/New_York")
    now = datetime.now(nyc)
    
    # Check if it's a weekday
    if now.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        logging.info("Market is closed (weekend)")
        return False
    
    # Check market hours (9:30 AM - 3:55 PM EST)
    if now.hour < 9 or (now.hour == 9 and now.minute < 30) or now.hour >= 16:
        logging.info("Market is closed (outside trading hours)")
        return False
    
    return True

def main():
    logging.info("Starting trading bot...")
    
    # Validate environment variables
    if not validate_environment():
        sys.exit(1)
    
    # Check if market is open
    if not is_market_open():
        logging.info("Market is closed. Exiting.")
        sys.exit(0)
    
    # Initialize API
    try:
        api = tradeapi.REST(
            os.getenv('APCA_API_KEY_ID'),
            os.getenv('APCA_API_SECRET_KEY'),
            os.getenv('APCA_BASE_URL'),
            api_version="v2"
        )
        
        # Validate connection
        account = api.get_account()
        logging.info(f"✅ Successfully connected to Alpaca!")
        logging.info(f"Account status: {account.status}")
        logging.info(f"Cash Balance: ${account.cash}")
    except Exception as e:
        logging.error(f"❌ Connection error: {e}")
        sys.exit(1)

    symb = "SPY"

    # Enhanced risk management parameters
    MAX_POSITION_SIZE = 0.05  # Maximum 5% of portfolio per trade
    ATR_PERIOD = 14
    RSI_PERIOD = 14
    EMA_FAST = 20
    EMA_SLOW = 50
    BB_PERIOD = 20
    BB_STD = 2

    def calculate_atr(high, low, close, period=ATR_PERIOD):
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    def calculate_ema(data, period):
        return data.ewm(span=period, adjust=False).mean()

    def calculate_bollinger_bands(data, period=BB_PERIOD, std=BB_STD):
        sma = data.rolling(window=period).mean()
        std_dev = data.rolling(window=period).std()
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        return upper_band, sma, lower_band

    try:
        # Fetch market data
        market_data = api.get_bars(symb, TimeFrame.Minute, limit=100).df

        if market_data.empty:
            logging.warning("⚠️ No market data retrieved. Exiting.")
            sys.exit(1)

        # Calculate technical indicators
        market_data['vwap'] = (market_data['close'] * market_data['volume']).cumsum() / market_data['volume'].cumsum()
        
        # RSI
        delta = market_data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
        rs = gain / loss
        market_data['rsi'] = 100 - (100 / (1 + rs))
        
        # EMAs
        market_data['ema_fast'] = calculate_ema(market_data['close'], EMA_FAST)
        market_data['ema_slow'] = calculate_ema(market_data['close'], EMA_SLOW)
        
        # Bollinger Bands
        market_data['bb_upper'], market_data['bb_middle'], market_data['bb_lower'] = calculate_bollinger_bands(market_data['close'])
        
        # ATR
        market_data['atr'] = calculate_atr(market_data['high'], market_data['low'], market_data['close'])
        
        # Get latest values
        last_price = market_data['close'].iloc[-1]
        vwap = market_data['vwap'].iloc[-1]
        rsi = market_data['rsi'].iloc[-1]
        ema_fast = market_data['ema_fast'].iloc[-1]
        ema_slow = market_data['ema_slow'].iloc[-1]
        atr = market_data['atr'].iloc[-1]
        bb_upper = market_data['bb_upper'].iloc[-1]
        bb_lower = market_data['bb_lower'].iloc[-1]

        logging.info(f"📊 Market Data - Price: {last_price:.2f}, VWAP: {vwap:.2f}, RSI: {rsi:.2f}")
        logging.info(f"📈 EMAs - Fast: {ema_fast:.2f}, Slow: {ema_slow:.2f}")
        logging.info(f"📊 ATR: {atr:.2f}")

        # Get current position
        position_qty = 0
        try:
            position = api.get_position(symb)
            position_qty = int(position.qty)
            logging.info(f"Current position: {position_qty} shares")
        except tradeapi.rest.APIError:
            logging.info("No open position")

        # Dynamic position sizing based on ATR
        account = api.get_account()
        balance = float(account.cash)
        risk_per_trade = 0.02  # 2% risk per trade
        position_size = min(MAX_POSITION_SIZE, risk_per_trade / (atr / last_price))
        order_size = max(1, int(balance * position_size / last_price))

        # Trading logic
        if (last_price < vwap and  # Price below VWAP
            rsi < 30 and  # Oversold
            ema_fast > ema_slow and  # Uptrend
            last_price < bb_lower and  # Price below lower BB
            position_qty == 0):  # No existing position
            
            logging.info(f"✅ Placing Buy Order for {order_size} shares.")
            api.submit_order(symbol=symb, qty=order_size, side="buy", type="market", time_in_force="gtc")
            logging.info(f"✅ Buy order placed at {last_price}.")

        elif (last_price > vwap and  # Price above VWAP
              rsi > 70 and  # Overbought
              ema_fast < ema_slow and  # Downtrend
              last_price > bb_upper and  # Price above upper BB
              position_qty > 0):  # Has existing position
            
            logging.info(f"✅ Placing Sell Order for {position_qty} shares.")
            api.submit_order(symbol=symb, qty=position_qty, side="sell", type="market", time_in_force="gtc")
            logging.info(f"✅ Sell order placed at {last_price}.")

        # Position management
        if position_qty > 0:
            avg_entry_price = float(position.avg_entry_price)
            
            # Dynamic stop loss (2 ATR below entry)
            stop_loss_price = avg_entry_price - (2 * atr)
            if last_price <= stop_loss_price:
                logging.info(f"❌ Stop loss triggered. Selling {position_qty} shares at {last_price}.")
                api.submit_order(symbol=symb, qty=position_qty, side="sell", type="market", time_in_force="gtc")
                logging.info("✅ Stop loss executed.")

            # Dynamic take profit (3 ATR above entry)
            take_profit_price = avg_entry_price + (3 * atr)
            if last_price >= take_profit_price:
                logging.info(f"✅ Take profit triggered. Selling {position_qty} shares at {last_price}.")
                api.submit_order(symbol=symb, qty=position_qty, side="sell", type="market", time_in_force="gtc")
                logging.info("✅ Take profit executed.")

        logging.info("Trading cycle completed successfully")

    except tradeapi.rest.APIError as e:
        logging.error(f"❌ APIError: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"⚠️ Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

