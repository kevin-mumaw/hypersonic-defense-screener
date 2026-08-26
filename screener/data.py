# data.py
# Pulls historical price data for all tickers in the universe
# Source: yfinance with retry logic and delays
# Cloud deployment: fundamentals use cache file to avoid rate limiting

import yfinance as yf
import pandas as pd
import time
import random
import os
from universe import UNIVERSE


def fetch_price_data(ticker, period="6mo", interval="1d"):
    """
    Fetch historical OHLCV data for a single ticker.
    Includes retry logic for rate limiting.
    """
    max_retries = 3

    for attempt in range(max_retries):
        try:
            if attempt > 0:
                wait = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait)

            data = yf.download(ticker, period=period,
                              interval=interval, progress=False)
            if data.empty:
                print(f"  WARNING: No data returned for {ticker}")
                return None
            return data

        except Exception as e:
            if attempt == max_retries - 1:
                print(f"  ERROR fetching {ticker}: {e}")
                return None
            continue

    return None


def fetch_universe_data(period="6mo", interval="1d"):
    """
    Fetch price data for all tickers in the universe.
    """
    print(f"Fetching price data for {len(UNIVERSE)} tickers...")
    print(f"Period: {period} | Interval: {interval} | Source: yfinance\n")

    results = {}
    failed  = []

    for ticker in UNIVERSE.keys():
        time.sleep(random.uniform(0.5, 1.5))

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

    print("\n--- Latest Close Prices ---")
    for ticker, df in data.items():
        latest_close = df["Close"].iloc[-1].item()
        print(f"  {ticker:<6} — ${latest_close:.2f}")