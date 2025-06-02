from abc import ABC, abstractmethod
import logging

class BaseStrategy(ABC):
    def __init__(self, api, symbol, account):
        self.api = api
        self.symbol = symbol
        self.account = account
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def generate_signals(self, data):
        """Generate trading signals based on market data"""
        pass
    
    @abstractmethod
    def calculate_position_size(self, signal_strength):
        """Calculate position size based on signal strength"""
        pass
    
    @abstractmethod
    def calculate_stop_loss(self, entry_price, position_type):
        """Calculate stop loss level"""
        pass
    
    @abstractmethod
    def calculate_take_profit(self, entry_price, position_type):
        """Calculate take profit level"""
        pass
    
    def place_order(self, side, qty, stop_loss=None, take_profit=None):
        """Place an order with optional stop loss and take profit"""
        try:
            # Place main order
            order = self.api.submit_order(
                symbol=self.symbol,
                qty=qty,
                side=side,
                type='market',
                time_in_force='gtc'
            )
            
            # Place stop loss if specified
            if stop_loss:
                self.api.submit_order(
                    symbol=self.symbol,
                    qty=qty,
                    side='sell' if side == 'buy' else 'buy',
                    type='stop',
                    time_in_force='gtc',
                    stop_price=stop_loss
                )
            
            # Place take profit if specified
            if take_profit:
                self.api.submit_order(
                    symbol=self.symbol,
                    qty=qty,
                    side='sell' if side == 'buy' else 'buy',
                    type='limit',
                    time_in_force='gtc',
                    limit_price=take_profit
                )
            
            self.logger.info(f"Order placed: {side} {qty} {self.symbol}")
            return order
            
        except Exception as e:
            self.logger.error(f"Error placing order: {str(e)}")
            return None
    
    def close_position(self):
        """Close all positions for the symbol"""
        try:
            position = self.api.get_position(self.symbol)
            qty = int(position.qty)
            if qty > 0:
                self.api.submit_order(
                    symbol=self.symbol,
                    qty=qty,
                    side='sell',
                    type='market',
                    time_in_force='gtc'
                )
                self.logger.info(f"Position closed: {qty} {self.symbol}")
        except Exception as e:
            self.logger.info(f"No position to close: {str(e)}")
    
    def get_position(self):
        """Get current position for the symbol"""
        try:
            return self.api.get_position(self.symbol)
        except Exception:
            return None 