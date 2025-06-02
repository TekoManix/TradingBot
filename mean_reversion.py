from .base_strategy import BaseStrategy
import numpy as np

class MeanReversionStrategy(BaseStrategy):
    def __init__(self, api, symbol, account):
        super().__init__(api, symbol, account)
        self.max_position_size = 0.05  # Maximum 5% of portfolio
        self.risk_per_trade = 0.01     # 1% risk per trade
    
    def generate_signals(self, data):
        """Generate trading signals based on mean reversion strategy"""
        # Get latest data
        hourly_data = data['1h']
        
        # Calculate mean reversion indicators
        rsi = hourly_data['rsi'].iloc[-1]
        bb_upper = hourly_data['bb_upper'].iloc[-1]
        bb_lower = hourly_data['bb_lower'].iloc[-1]
        bb_middle = hourly_data['bb_middle'].iloc[-1]
        price = hourly_data['close'].iloc[-1]
        vwap = hourly_data['vwap'].iloc[-1]
        
        # Calculate volatility
        atr = hourly_data['atr'].iloc[-1]
        avg_atr = hourly_data['atr'].rolling(20).mean().iloc[-1]
        
        # Generate signals
        long_signal = (
            rsi < 30 and                    # Oversold
            price < bb_lower and            # Price below lower BB
            price < vwap and                # Price below VWAP
            atr < avg_atr                   # Low volatility
        )
        
        short_signal = (
            rsi > 70 and                    # Overbought
            price > bb_upper and            # Price above upper BB
            price > vwap and                # Price above VWAP
            atr < avg_atr                   # Low volatility
        )
        
        # Calculate signal strength
        signal_strength = 0
        if long_signal:
            # Stronger signal when price is further from mean
            deviation = (bb_middle - price) / bb_middle
            signal_strength = min(1.0, deviation * 2)
        elif short_signal:
            # Stronger signal when price is further from mean
            deviation = (price - bb_middle) / bb_middle
            signal_strength = -min(1.0, deviation * 2)
        
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
        win_rate = 0.55  # Estimated win rate (lower for mean reversion)
        avg_win = 0.015  # Estimated average win (1.5%)
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
        atr = float(self.api.get_bars(self.symbol, '1h', limit=1).df['atr'].iloc[-1])
        
        if position_type == 'long':
            return entry_price - (2 * atr)
        else:
            return entry_price + (2 * atr)
    
    def calculate_take_profit(self, entry_price, position_type):
        """Calculate mean reversion take profit"""
        # Get Bollinger Bands
        bb_data = self.api.get_bars(self.symbol, '1h', limit=1).df
        bb_middle = bb_data['bb_middle'].iloc[-1]
        
        if position_type == 'long':
            return bb_middle  # Target the middle band
        else:
            return bb_middle  # Target the middle band 