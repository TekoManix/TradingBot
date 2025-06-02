import numpy as np
import pandas as pd

def calculate_atr(high, low, close, period=14):
    """Calculate Average True Range"""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calculate_rsi(close, period=14):
    """Calculate Relative Strength Index"""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(close, fast=12, slow=26, signal=9):
    """Calculate MACD, Signal line, and Histogram"""
    exp1 = close.ewm(span=fast, adjust=False).mean()
    exp2 = close.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    return macd, signal_line, histogram

def calculate_bollinger_bands(close, period=20, std=2):
    """Calculate Bollinger Bands"""
    sma = close.rolling(window=period).mean()
    std_dev = close.rolling(window=period).std()
    upper_band = sma + (std_dev * std)
    lower_band = sma - (std_dev * std)
    return upper_band, sma, lower_band

def calculate_vwap(high, low, close, volume):
    """Calculate Volume Weighted Average Price"""
    typical_price = (high + low + close) / 3
    return (typical_price * volume).cumsum() / volume.cumsum()

def calculate_adx(high, low, close, period=14):
    """Calculate Average Directional Index"""
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Directional Movement
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    
    # Smoothed Averages
    tr_smoothed = tr.rolling(period).sum()
    plus_di = 100 * pd.Series(plus_dm).rolling(period).sum() / tr_smoothed
    minus_di = 100 * pd.Series(minus_dm).rolling(period).sum() / tr_smoothed
    
    # ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(period).mean()
    
    return adx, plus_di, minus_di

def calculate_volume_profile(high, low, close, volume, num_bins=50):
    """Calculate Volume Profile"""
    price_range = np.linspace(low.min(), high.max(), num_bins)
    volume_profile = np.zeros(num_bins-1)
    
    for i in range(len(close)):
        price = close[i]
        vol = volume[i]
        bin_index = np.digitize(price, price_range) - 1
        if 0 <= bin_index < len(volume_profile):
            volume_profile[bin_index] += vol
    
    poc_index = np.argmax(volume_profile)
    poc_price = price_range[poc_index]
    
    return {
        'volume_profile': volume_profile,
        'price_range': price_range,
        'poc_price': poc_price
    }

def calculate_support_resistance(high, low, close, volume, num_levels=5):
    """Calculate Support and Resistance levels"""
    # Use price action and volume to identify levels
    price_range = np.linspace(low.min(), high.max(), 100)
    volume_profile = np.zeros(99)
    
    for i in range(len(close)):
        price = close[i]
        vol = volume[i]
        bin_index = np.digitize(price, price_range) - 1
        if 0 <= bin_index < len(volume_profile):
            volume_profile[bin_index] += vol
    
    # Find local maxima in volume profile
    from scipy.signal import find_peaks
    peaks, _ = find_peaks(volume_profile, distance=10)
    
    # Sort peaks by volume
    peak_volumes = volume_profile[peaks]
    sorted_indices = np.argsort(peak_volumes)[::-1]
    top_peaks = peaks[sorted_indices[:num_levels]]
    
    levels = price_range[top_peaks]
    return sorted(levels) 