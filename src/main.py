import os
import sys
import logging
import alpaca_trade_api as tradeapi
from datetime import datetime
from dotenv import load_dotenv
from alpaca_trade_api.rest import TimeFrame

from analysis.market_analysis import (
    detect_market_regime,
    analyze_order_flow,
    analyze_market_microstructure,
    is_market_open,
    get_market_data
)
from strategies.trend_following import TrendFollowingStrategy
from strategies.mean_reversion import MeanReversionStrategy

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def initialize_api():
    """Initialize and validate API connection"""
    # Load environment variables
    load_dotenv()
    
    # Get API credentials
    api_key = os.getenv('APCA_API_KEY_ID')
    api_secret = os.getenv('APCA_API_SECRET_KEY')
    base_url = os.getenv('APCA_BASE_URL')
    
    if not all([api_key, api_secret, base_url]):
        logging.error("Missing API credentials")
        sys.exit(1)
    
    # Initialize API
    api = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')
    
    # Validate connection
    try:
        account = api.get_account()
        logging.info(f"✅ Successfully connected to Alpaca!")
        logging.info(f"Account status: {account.status}")
        logging.info(f"Cash Balance: ${account.cash}")
        return api, account
    except Exception as e:
        logging.error(f"❌ Connection error: {e}")
        sys.exit(1)

def main():
    """Main trading bot function"""
    # Initialize API
    api, account = initialize_api()
    
    # Check if market is open
    if not is_market_open():
        logging.info("Market is closed. Exiting.")
        sys.exit(0)
    
    # Trading parameters
    symbol = "SPY"
    timeframes = {
        '1m': TimeFrame.Minute,
        '5m': TimeFrame.Minute,
        '15m': TimeFrame.Minute,
        '1h': TimeFrame.Hour,
        '1d': TimeFrame.Day
    }
    
    try:
        # Get market data
        data = get_market_data(api, symbol, timeframes)
        
        # Detect market regime
        regime = detect_market_regime(data['1d'])
        logging.info(f"Market regime: {'Trending' if regime['is_trending'] else 'Ranging' if regime['is_ranging'] else 'Volatile'}")
        
        # Select strategy based on market regime
        if regime['is_trending']:
            strategy = TrendFollowingStrategy(api, symbol, account)
            logging.info("Using Trend Following Strategy")
        else:
            strategy = MeanReversionStrategy(api, symbol, account)
            logging.info("Using Mean Reversion Strategy")
        
        # Get current position
        position = strategy.get_position()
        
        if position:
            # Manage existing position
            entry_price = float(position.avg_entry_price)
            current_price = float(api.get_latest_trade(symbol).price)
            
            # Calculate stop loss and take profit
            stop_loss = strategy.calculate_stop_loss(entry_price, 'long' if float(position.qty) > 0 else 'short')
            take_profit = strategy.calculate_take_profit(entry_price, 'long' if float(position.qty) > 0 else 'short')
            
            # Check if we should exit
            if (float(position.qty) > 0 and current_price <= stop_loss) or \
               (float(position.qty) < 0 and current_price >= stop_loss) or \
               (float(position.qty) > 0 and current_price >= take_profit) or \
               (float(position.qty) < 0 and current_price <= take_profit):
                strategy.close_position()
                logging.info("Position closed based on stop loss or take profit")
        else:
            # Generate new signals
            signals = strategy.generate_signals(data)
            
            if signals['signal']:
                # Calculate position size
                qty = strategy.calculate_position_size(signals['strength'])
                
                # Calculate stop loss and take profit
                stop_loss = strategy.calculate_stop_loss(signals['price'], signals['signal'])
                take_profit = strategy.calculate_take_profit(signals['price'], signals['signal'])
                
                # Place order
                order = strategy.place_order(
                    side=signals['signal'],
                    qty=qty,
                    stop_loss=stop_loss,
                    take_profit=take_profit
                )
                
                if order:
                    logging.info(f"Order placed: {signals['signal']} {qty} {symbol}")
                    logging.info(f"Entry: {signals['price']:.2f}, Stop: {stop_loss:.2f}, Target: {take_profit:.2f}")
        
        logging.info("Trading cycle completed successfully")
        
    except Exception as e:
        logging.error(f"Error in main trading loop: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 