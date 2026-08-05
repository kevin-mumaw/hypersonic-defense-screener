# data.py
# Pulls historical price data for all tickers in the universe
# Primary source: Schwab API (reliable, no rate limiting)
# Fallback source: yfinance (local use only)

import pandas as pd
import yfinance as yf
import time
import random
import os
import schwab
from dotenv import load_dotenv
from universe import UNIVERSE

load_dotenv()

SCHWAB_APP_KEY    = os.getenv("SCHWAB_APP_KEY", "")
SCHWAB_APP_SECRET = os.getenv("SCHWAB_APP_SECRET", "")
TOKEN_PATH        = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "token.json"
)


def get_schwab_client():
    """
    Get authenticated Schwab client.
    On cloud: uses refresh token from Streamlit secrets.
    Locally: uses token.json file.
    Returns None if credentials not available.
    """
    if not SCHWAB_APP_KEY or not SCHWAB_APP_SECRET:
        return None

    # Try Streamlit secrets first (cloud deployment)
    try:
        import streamlit as st
        refresh_token = st.secrets.get("SCHWAB_REFRESH_TOKEN", "")
        if refresh_token:
            import json
            import tempfile
            token_data = {
                "creation_timestamp": 0,
                "token": {
                    "expires_in": 1800,
                    "token_type": "Bearer",
                    "scope": "api",
                    "refresh_token": refresh_token,
                    "access_token": "",
                    "expires_at": 0
                }
            }
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.json', delete=False
            ) as f:
                json.dump(token_data, f)
                temp_path = f.name

            client = schwab.auth.client_from_token_file(
                temp_path,
                SCHWAB_APP_KEY,
                SCHWAB_APP_SECRET
            )
            os.unlink(temp_path)
            return client
    except Exception:
        pass

    # Fall back to local token file
    if not os.path.exists(TOKEN_PATH):
        return None
    try:
        client = schwab.auth.client_from_token_file(
            TOKEN_PATH,
            SCHWAB_APP_KEY,
            SCHWAB_APP_SECRET
        )
        return client
    except Exception as e:
        print(f"  WARNING: Schwab auth failed: {e}")
        return None
def fetch_price_data_schwab(client, ticker, period="6mo"):
    """
    Fetch historical OHLCV data from Schwab API.

    Args:
        client : authenticated Schwab client
        ticker : stock symbol
        period : lookback period (1mo, 3mo, 6mo, 1y, 2y)

    Returns:
        pandas DataFrame with OHLCV data, or None if fetch fails
    """
    from schwab.client import Client

    # Map period to Schwab period type and frequency
    period_map = {
        "1mo" : (1,  Client.PriceHistory.Period.ONE_MONTH,
                      Client.PriceHistory.Frequency.DAILY,
                      Client.PriceHistory.FrequencyType.DAILY),
        "3mo" : (3,  Client.PriceHistory.Period.THREE_MONTHS,
                      Client.PriceHistory.Frequency.DAILY,
                      Client.PriceHistory.FrequencyType.DAILY),
        "6mo" : (6,  Client.PriceHistory.Period.SIX_MONTHS,
                      Client.PriceHistory.Frequency.DAILY,
                      Client.PriceHistory.FrequencyType.DAILY),
        "1y"  : (1,  Client.PriceHistory.Period.ONE_YEAR,
                      Client.PriceHistory.Frequency.DAILY,
                      Client.PriceHistory.FrequencyType.DAILY),
        "2y"  : (2,  Client.PriceHistory.Period.TWO_YEARS,
                      Client.PriceHistory.Frequency.DAILY,
                      Client.PriceHistory.FrequencyType.DAILY),
        "5y"  : (5,  Client.PriceHistory.Period.FIVE_YEARS,
                      Client.PriceHistory.Frequency.WEEKLY,
                      Client.PriceHistory.FrequencyType.WEEKLY),
    }

    if period not in period_map:
        period = "6mo"

    p_count, p_type, freq, freq_type = period_map[period]

    try:
        resp = client.get_price_history(
            ticker,
            period_type=Client.PriceHistory.PeriodType.MONTH
                if period in ("1mo","3mo","6mo")
                else Client.PriceHistory.PeriodType.YEAR,
            period=p_type,
            frequency_type=freq_type,
            frequency=freq,
            need_extended_hours_data=False,
        )

        if resp.status_code != 200:
            return None

        data = resp.json()
        candles = data.get("candles", [])

        if not candles:
            return None

        df = pd.DataFrame(candles)
        df["datetime"] = pd.to_datetime(df["datetime"], unit="ms")
        df = df.set_index("datetime")
        df = df.rename(columns={
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
    Tries Schwab first, falls back to yfinance.
    """
    client = get_schwab_client()

    if client:
        data = fetch_price_data_schwab(client, ticker, period)
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
    """
    client = get_schwab_client()
    source = "Schwab" if client else "yfinance"

    print(f"Fetching price data for {len(UNIVERSE)} tickers...")
    print(f"Period: {period} | Interval: {interval} | Source: {source}\n")

    results = {}
    failed  = []

    for ticker in UNIVERSE.keys():
        if not client:
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