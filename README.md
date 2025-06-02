# Alpaca Trading Bot

An automated trading bot that uses technical analysis to trade SPY on the Alpaca platform. The bot implements a strategy based on VWAP, RSI, EMAs, and Bollinger Bands with dynamic position sizing and risk management.

## Features

- Automated trading during market hours
- Technical analysis using multiple indicators:
  - VWAP (Volume Weighted Average Price)
  - RSI (Relative Strength Index)
  - EMAs (Exponential Moving Averages)
  - Bollinger Bands
  - ATR (Average True Range)
- Dynamic position sizing based on volatility
- Risk management with dynamic stop-loss and take-profit levels
- GitHub Actions integration for automated execution

## Setup

1. Fork this repository
2. Add your Alpaca API credentials as GitHub Secrets:
   - `APCA_API_KEY_ID`
   - `APCA_API_SECRET_KEY`
   - `APCA_BASE_URL` (use `https://paper-api.alpaca.markets` for paper trading)

## Local Development

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your Alpaca credentials:
   ```
   APCA_API_KEY_ID=your_api_key_here
   APCA_API_SECRET_KEY=your_secret_key_here
   APCA_BASE_URL=https://paper-api.alpaca.markets
   ```
5. Run the bot:
   ```bash
   python bot.py
   ```

## Trading Strategy

The bot implements the following strategy:

### Entry Conditions
- Price below VWAP
- RSI < 30 (oversold)
- Fast EMA above Slow EMA (uptrend)
- Price below lower Bollinger Band

### Exit Conditions
- Price above VWAP
- RSI > 70 (overbought)
- Fast EMA below Slow EMA (downtrend)
- Price above upper Bollinger Band

### Risk Management
- Maximum position size: 5% of portfolio
- Dynamic stop-loss: 2 ATR below entry
- Dynamic take-profit: 3 ATR above entry
- Risk per trade: 2% of account

## GitHub Actions

The bot runs automatically via GitHub Actions:
- At market open (9:30 AM EST)
- At market close (3:55 PM EST)
- Can be triggered manually via workflow_dispatch

## Logging

The bot logs all activities to both:
- Console output
- `trading_bot.log` file

## Disclaimer

This trading bot is for educational purposes only. Use at your own risk. Past performance is not indicative of future results. 