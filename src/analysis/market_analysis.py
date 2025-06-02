import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from .technical_indicators import (
    calculate_atr, calculate_rsi, calculate_macd,
    calculate_bollinger_bands, calculate_vwap,
    calculate_adx, calculate_volume_profile,
    calculate_support_resistance
)

def detect_market_regime(data, lookback=20):
    """Detect current market regime (trending, ranging, volatile)"""
    # Calculate volatility
    returns = data['close'].pct_change()
    volatility = returns.rolling(lookback).std()
    
    # Calculate ADX for trend strength
    adx, plus_di, minus_di = calculate_adx(data['high'], data['low'], data['close'])
    
    # Calculate price range
    price_range = (data['high'] - data['low']).rolling(lookback).mean()
    
    # Determine regime
    is_trending = adx > 25
    is_volatile = volatility > volatility.rolling(100).mean()
    is_ranging = ~is_trending & ~is_volatile
    
    return {
        'volatility': volatility,
        'adx': adx,
        'is_trending': is_trending,
        'is_volatile': is_volatile,
        'is_ranging': is_ranging,
        'trend_direction': np.where(plus_di > minus_di, 1, -1)
    }

def analyze_order_flow(data):
    """Analyze order flow and market microstructure"""
    # Calculate buying and selling pressure
    typical_price = (data['high'] + data['low'] + data['close']) / 3
    money_flow = typical_price * data['volume']
    
    # Calculate buying/selling pressure
    price_change = data['close'].diff()
    volume_change = data['volume'].diff()
    
    buying_pressure = np.where(
        (price_change > 0) & (volume_change > 0),
        money_flow,
        0
    )
    
    selling_pressure = np.where(
        (price_change < 0) & (volume_change > 0),
        money_flow,
        0
    )
    
    # Calculate spread
    spread = (data['high'] - data['low']) / data['close']
    avg_spread = spread.rolling(20).mean()
    
    return {
        'buying_pressure': buying_pressure.sum() / money_flow.sum(),
        'selling_pressure': selling_pressure.sum() / money_flow.sum(),
        'spread': spread.iloc[-1],
        'avg_spread': avg_spread.iloc[-1]
    }

def analyze_market_microstructure(data):
    """Analyze market microstructure"""
    # Calculate bid-ask spread proxy
    spread = (data['high'] - data['low']) / data['close']
    
    # Calculate volume profile
    volume_profile = calculate_volume_profile(
        data['high'], data['low'], data['close'], data['volume']
    )
    
    # Calculate support and resistance levels
    levels = calculate_support_resistance(
        data['high'], data['low'], data['close'], data['volume']
    )
    
    return {
        'spread': spread.iloc[-1],
        'avg_spread': spread.rolling(20).mean().iloc[-1],
        'volume_profile': volume_profile,
        'support_resistance': levels
    }

def is_market_open():
    """Check if the market is currently open"""
    nyc = pytz.timezone("America/New_York")
    now = datetime.now(nyc)
    
    # Check if it's a weekday
    if now.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return False
    
    # Check market hours (9:30 AM - 3:55 PM EST)
    if now.hour < 9 or (now.hour == 9 and now.minute < 30) or now.hour >= 16:
        return False
    
    return True

def get_market_data(api, symbol, timeframes):
    """Get market data for multiple timeframes"""
    data = {}
    
    for tf, timeframe in timeframes.items():
        if tf in ['1m', '5m', '15m']:
            multiplier = int(tf[:-1])
            data[tf] = api.get_bars(
                symbol, timeframe, limit=100,
                adjustment='raw', multiplier=multiplier
            ).df
        else:
            data[tf] = api.get_bars(
                symbol, timeframe, limit=100,
                adjustment='raw'
            ).df
        
        # Calculate indicators for each timeframe
        data[tf]['rsi'] = calculate_rsi(data[tf]['close'])
        data[tf]['macd'], data[tf]['macd_signal'], _ = calculate_macd(data[tf]['close'])
        data[tf]['bb_upper'], data[tf]['bb_middle'], data[tf]['bb_lower'] = calculate_bollinger_bands(data[tf]['close'])
        data[tf]['vwap'] = calculate_vwap(data[tf]['high'], data[tf]['low'], data[tf]['close'], data[tf]['volume'])
        data[tf]['atr'] = calculate_atr(data[tf]['high'], data[tf]['low'], data[tf]['close'])
    
    return data 