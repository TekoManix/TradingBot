from .base_strategy import BaseStrategy
import numpy as np

class TrendFollowingStrategy(BaseStrategy):
    def __init__(self, api, symbol, account):
        super().__init__(api, symbol, account)
        self.max_position_size = 0.1  # Maximum 10% of portfolio
        self.risk_per_trade = 0.02    # 2% risk per trade
    
    def generate_signals(self, data):
        """Generate trading signals based on trend following strategy"""
        # Get latest data
        daily_data = data['1d']
        hourly_data = data['1h']
        
        # Calculate trend strength
        adx = daily_data['adx'].iloc[-1]
        plus_di = daily_data['plus_di'].iloc[-1]
        minus_di = daily_data['minus_di'].iloc[-1]
        
        # Calculate momentum
        macd = hourly_data['macd'].iloc[-1]
        macd_signal = hourly_data['macd_signal'].iloc[-1]
        
        # Calculate price action
        price = daily_data['close'].iloc[-1]
        vwap = daily_data['vwap'].iloc[-1]
        bb_upper = daily_data['bb_upper'].iloc[-1]
        bb_lower = daily_data['bb_lower'].iloc[-1]
        
        # Generate signals
        long_signal = (
            adx > 25 and                    # Strong trend
            plus_di > minus_di and          # Uptrend
            macd > macd_signal and          # MACD crossover
            price > vwap and                # Price above VWAP
            price < bb_upper                # Not overbought
        )
        
        short_signal = (
            adx > 25 and                    # Strong trend
            minus_di > plus_di and          # Downtrend
            macd < macd_signal and          # MACD crossover
            price < vwap and                # Price below VWAP
            price > bb_lower                # Not oversold
        )
        
        # Calculate signal strength
        signal_strength = 0
        if long_signal:
            signal_strength = min(1.0, (adx / 100) * (plus_di / (plus_di + minus_di)))
        elif short_signal:
            signal_strength = -min(1.0, (adx / 100) * (minus_di / (plus_di + minus_di)))
        
        return {
            'signal': 'long' if long_signal else 'short' if short_signal else None,
            'strength': signal_strength,
            'price': price,
            'vwap': vwap
        }
    
    def calculate_position_size(self, signal_strength):
        """Calculate position size based on signal strength and risk management"""
        # Get account equity
        equity = float(self.account.equity)
        
        # Calculate base position size using Kelly Criterion
        win_rate = 0.6  # Estimated win rate
        avg_win = 0.02  # Estimated average win (2%)
        avg_loss = 0.01  # Estimated average loss (1%)
        
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        
        # Adjust for signal strength
        adjusted_kelly = kelly_fraction * abs(signal_strength)
        
        # Apply maximum position size limit
        position_size = min(adjusted_kelly, self.max_position_size)
        
        # Calculate position size in dollars
        position_value = equity * position_size
        
        # Get current price
        price = float(self.api.get_latest_trade(self.symbol).price)
        
        # Calculate number of shares
        shares = int(position_value / price)
        
        return max(1, shares)  # Minimum 1 share
    
    def calculate_stop_loss(self, entry_price, position_type):
        """Calculate ATR-based stop loss"""
        # Get ATR
        atr = float(self.api.get_bars(self.symbol, '1d', limit=1).df['atr'].iloc[-1])
        
        if position_type == 'long':
            return entry_price - (2.5 * atr)
        else:
            return entry_price + (2.5 * atr)
    
    def calculate_take_profit(self, entry_price, position_type):
        """Calculate ATR-based take profit"""
        # Get ATR
        atr = float(self.api.get_bars(self.symbol, '1d', limit=1).df['atr'].iloc[-1])
        
        if position_type == 'long':
            return entry_price + (3 * atr)
        else:
            return entry_price - (3 * atr) 