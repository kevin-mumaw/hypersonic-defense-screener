# data.py
# Pulls historical price data for all tickers in the universe
# Primary source: Tradier API (works on cloud platforms)
# Fallback source: yfinance (local use only)
# Fundamentals still use yfinance — local only

import requests
import pandas as pd
import yfinance as yf
import time
import random
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from universe import UNIVERSE

load_dotenv()

try:
    import streamlit as st
    TRADIER_TOKEN = st.secrets.get("TRADIER_TOKEN", os.getenv("TRADIER_TOKEN", ""))
except Exception:
    TRADIER_TOKEN = os.getenv("TRADIER_TOKEN", "")
TRADIER_BASE  = "https://api.tradier.com/v1"


def fetch_price_data_tradier(ticker, period="6mo", interval="1d"):
    """
    Fetch historical OHLCV data from Tradier API.
    Works on cloud platforms — no rate limiting issues.

    Args:
        ticker  : stock symbol
        period  : lookback period (1mo, 3mo, 6mo, 1y, 2y)
        interval: data frequency (daily, weekly)

    Returns:
        pandas DataFrame with OHLCV data, or None if fetch fails
    """
    if not TRADIER_TOKEN:
        return None

    # Convert period to start date
    period_days = {
        "1mo": 30, "3mo": 90, "6mo": 180,
        "1y": 365, "2y": 730, "5y": 1825
    }
    days     = period_days.get(period, 180)
    end_dt   = datetime.today()
    start_dt = end_dt - timedelta(days=days)

    start_str = start_dt.strftime("%Y-%m-%d")
    end_str   = end_dt.strftime("%Y-%m-%d")

    # Tradier interval mapping
    tradier_interval = "daily" if interval == "1d" else "weekly"

    url = f"{TRADIER_BASE}/markets/history"
    headers = {
        "Authorization": f"Bearer {TRADIER_TOKEN}",
        "Accept"       : "application/json",
    }
    params = {
        "symbol"  : ticker,
        "interval": tradier_interval,
        "start"   : start_str,
        "end"     : end_str,
    }

    try:
        response = requests.get(url, headers=headers,
                               params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        history = data.get("history", {})
        if not history or history == "null":
            return None

        days_data = history.get("day", [])
        if not days_data:
            return None

        # Convert to DataFrame matching yfinance format
        if isinstance(days_data, dict):
            days_data = [days_data]

        df = pd.DataFrame(days_data)
        df["date"]   = pd.to_datetime(df["date"])
        df           = df.set_index("date")
        df           = df.rename(columns={
            "open"  : "Open",
            "high"  : "High",
            "low"   : "Low",
            "close" : "Close",
            "volume": "Volume",
        })
        df = df[["Open", "High", "Low", "Close", "Volume"]]
        df = df.sort_index()

        return df

    except Exception as e:
        return None


def fetch_price_data_yfinance(ticker, period="6mo", interval="1d"):
    """
    Fetch historical OHLCV data from yfinance.
    Fallback for local use — rate limited on cloud platforms.
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
                return None
            return data

        except Exception as e:
            if attempt == max_retries - 1:
                return None
            continue

    return None


def fetch_price_data(ticker, period="6mo", interval="1d"):
    """
    Fetch historical OHLCV data for a single ticker.
    Tries Tradier first, falls back to yfinance.

    Args:
        ticker  : stock symbol
        period  : lookback period
        interval: data frequency

    Returns:
        pandas DataFrame with OHLCV data, or None if fetch fails
    """
    # Try Tradier first
    if TRADIER_TOKEN:
        data = fetch_price_data_tradier(ticker, period, interval)
        if data is not None and not data.empty:
            return data

    # Fall back to yfinance
    data = fetch_price_data_yfinance(ticker, period, interval)
    if data is not None:
        return data

    print(f"  WARNING: No data returned for {ticker}")
    return None


def fetch_universe_data(period="6mo", interval="1d"):
    """
    Fetch price data for all tickers in the universe.

    Returns:
        dict of {ticker: DataFrame}
    """
    source = "Tradier" if TRADIER_TOKEN else "yfinance"
    print(f"Fetching price data for {len(UNIVERSE)} tickers...")
    print(f"Period: {period} | Interval: {interval} | Source: {source}\n")

    results = {}
    failed  = []

    for ticker in UNIVERSE.keys():
        if not TRADIER_TOKEN:
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