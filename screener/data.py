# data.py
# Pulls historical price data for all tickers in the universe
# Data source: yfinance (free, sufficient for Phase 1)
# Note: yfinance data quality should be sanity-checked periodically

import yfinance as yf
import pandas as pd
from universe import UNIVERSE

def fetch_price_data(ticker, period="6mo", interval="1d"):
    """
    Fetch historical OHLCV data for a single ticker.
    
    Args:
        ticker  : stock symbol
        period  : lookback period (1mo, 3mo, 6mo, 1y, 2y)
        interval: data frequency (1d, 1wk)
    
    Returns:
        pandas DataFrame with OHLCV data, or None if fetch fails
    """
    try:
        data = yf.download(ticker, period=period, 
                          interval=interval, progress=False)
        if data.empty:
            print(f"  WARNING: No data returned for {ticker}")
            return None
        return data
    except Exception as e:
        print(f"  ERROR fetching {ticker}: {e}")
        return None


def fetch_universe_data(period="6mo", interval="1d"):
    """
    Fetch price data for all tickers in the universe.
    
    Returns:
        dict of {ticker: DataFrame}
    """
    print(f"Fetching price data for {len(UNIVERSE)} tickers...")
    print(f"Period: {period} | Interval: {interval}\n")
    
    results = {}
    failed = []

    for ticker in UNIVERSE.keys():
        data = fetch_price_data(ticker, period=period, 
                               interval=interval)
        if data is not None:
            results[ticker] = data
            print(f"  {ticker:<6} — {len(data)} rows fetched")
        else:
            failed.append(ticker)

    print(f"\nSuccess: {len(results)}/{len(UNIVERSE)} tickers")
    
    if failed:
        print(f"Failed:  {failed}")
    
    return results


if __name__ == "__main__":
    data = fetch_universe_data(period="6mo")
    
    # Sanity check — print last close for each ticker
    print("\n--- Latest Close Prices ---")
    for ticker, df in data.items():
        latest_close = df["Close"].iloc[-1].item()
        print(f"  {ticker:<6} — ${latest_close:.2f}")