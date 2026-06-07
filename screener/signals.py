# signals.py
# Calculates technical signals for all tickers in the universe
# Signals: MA20, MA50, MA200, RSI(14), Volume vs 20-day average
# These form the technical component (40%) of the composite score

import pandas as pd
import numpy as np
from data import fetch_universe_data


def calculate_rsi(series, period=14):
    """
    Calculate Relative Strength Index (RSI).
    
    Args:
        series : pandas Series of closing prices
        period : RSI lookback period (default 14)
    
    Returns:
        pandas Series of RSI values
    """
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_signals(ticker, df):
    """
    Calculate all technical signals for a single ticker.
    
    Args:
        ticker : stock symbol
        df     : OHLCV DataFrame from yfinance
    
    Returns:
        dict of signal values and interpretations
    """
    close = df["Close"].squeeze()
    volume = df["Volume"].squeeze()

    # Moving averages
    ma20  = close.rolling(window=20).mean()
    ma50  = close.rolling(window=50).mean()
    ma200 = close.rolling(window=200).mean()

    # RSI
    rsi = calculate_rsi(close)

    # Volume vs 20-day average
    vol_avg20 = volume.rolling(window=20).mean()

    # Latest values
    latest_close   = close.iloc[-1]
    latest_ma20    = ma20.iloc[-1]
    latest_ma50    = ma50.iloc[-1]
    latest_ma200   = ma200.iloc[-1]
    latest_rsi     = rsi.iloc[-1]
    latest_vol     = volume.iloc[-1]
    latest_vol_avg = vol_avg20.iloc[-1]

    # Signal interpretations
    above_ma20  = latest_close > latest_ma20
    above_ma50  = latest_close > latest_ma50
    above_ma200 = latest_close > latest_ma200 if not np.isnan(latest_ma200) else None
    ma20_vs_ma50 = latest_ma20 > latest_ma50  # Golden/death cross indicator
    vol_confirmed = latest_vol > latest_vol_avg

    # RSI interpretation
    if latest_rsi >= 70:
        rsi_signal = "OVERBOUGHT"
    elif latest_rsi <= 30:
        rsi_signal = "OVERSOLD"
    else:
        rsi_signal = "NEUTRAL"

    # Trend interpretation
    if above_ma50 and above_ma20:
        trend = "BULLISH"
    elif not above_ma50 and not above_ma20:
        trend = "BEARISH"
    else:
        trend = "MIXED"

    return {
        "ticker"       : ticker,
        "close"        : round(latest_close, 2),
        "ma20"         : round(latest_ma20, 2),
        "ma50"         : round(latest_ma50, 2),
        "ma200"        : round(latest_ma200, 2) if not np.isnan(latest_ma200) else None,
        "rsi"          : round(latest_rsi, 1),
        "rsi_signal"   : rsi_signal,
        "above_ma20"   : above_ma20,
        "above_ma50"   : above_ma50,
        "above_ma200"  : above_ma200,
        "ma20_vs_ma50" : ma20_vs_ma50,
        "vol_confirmed": vol_confirmed,
        "trend"        : trend,
    }


def calculate_universe_signals(period="6mo"):
    """
    Calculate technical signals for all tickers in the universe.
    
    Returns:
        dict of {ticker: signals_dict}
    """
    universe_data = fetch_universe_data(period=period)
    
    print("\n--- Technical Signals ---\n")
    print(f"{'Ticker':<6} {'Close':>8} {'MA20':>8} "
          f"{'MA50':>8} {'RSI':>6} {'RSI Sig':<12} "
          f"{'Trend':<8} {'Vol OK'}")
    print("-" * 75)

    all_signals = {}

    for ticker, df in universe_data.items():
        signals = calculate_signals(ticker, df)
        all_signals[ticker] = signals

        ma200_str = (f"${signals['ma200']:>7.2f}" 
                    if signals['ma200'] else "    N/A")
        
        print(
            f"{signals['ticker']:<6} "
            f"${signals['close']:>7.2f} "
            f"${signals['ma20']:>7.2f} "
            f"${signals['ma50']:>7.2f} "
            f"{signals['rsi']:>6.1f} "
            f"{signals['rsi_signal']:<12} "
            f"{signals['trend']:<8} "
            f"{'YES' if signals['vol_confirmed'] else 'NO'}"
        )

    return all_signals


if __name__ == "__main__":
    signals = calculate_universe_signals(period="6mo")
    