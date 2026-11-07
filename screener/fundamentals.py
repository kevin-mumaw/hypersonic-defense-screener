# fundamentals.py
# Fetches and scores fundamental data for all universe tickers
# Phase 2 Part A: Automated via yfinance (local) or cache (cloud)
# Uses cache file on cloud platforms to avoid rate limiting

import yfinance as yf
import pandas as pd
import os
import json
from datetime import date
from universe import UNIVERSE


# Fundamentals are refreshed weekly (Sunday workflow). A cache older
# than this is stale — fetch_universe_fundamentals warns loudly.
CACHE_MAX_AGE_DAYS = 7


def _cache_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root  = os.path.dirname(script_dir)
    return os.path.join(repo_root, "data", "fundamentals_cache.json")


def get_fundamentals_cache_info():
    """
    Describe the fundamentals cache without loading the data.

    Returns {"cached_date", "age_days", "stale", "source"} where
    source is "cache" when the file exists and "live" when there is
    no cache file (the next fetch goes to yfinance directly).
    """
    path = _cache_path()
    if not os.path.exists(path):
        return {"cached_date": None, "age_days": None,
                "stale": False, "source": "live"}
    try:
        with open(path, "r") as f:
            cache = json.load(f)
        cached_date = cache.get("_meta", {}).get("cached_date")
        if not cached_date:
            return {"cached_date": None, "age_days": None,
                    "stale": True, "source": "cache"}
        age_days = (date.today()
                    - date.fromisoformat(cached_date)).days
        return {"cached_date": cached_date, "age_days": age_days,
                "stale": age_days > CACHE_MAX_AGE_DAYS, "source": "cache"}
    except Exception:
        return {"cached_date": None, "age_days": None,
                "stale": True, "source": "cache"}


def fetch_fundamentals(ticker):
    """
    Fetch fundamental data for a single ticker via yfinance.

    Returns:
        dict of fundamental metrics or None if fetch fails
    """
    try:
        stock = yf.Ticker(ticker)
        info  = stock.info

        return {
            "ticker"          : ticker,
            "revenue_growth"  : info.get("revenueGrowth", None),
            "gross_margin"    : info.get("grossMargins", None),
            "operating_margin": info.get("operatingMargins", None),
            "profit_margin"   : info.get("profitMargins", None),
            "debt_to_equity"  : info.get("debtToEquity", None),
            "total_revenue"   : info.get("totalRevenue", None),
            "earnings_growth" : info.get("earningsGrowth", None),
            "roe"             : info.get("returnOnEquity", None),
        }

    except Exception as e:
        print(f"  ERROR fetching fundamentals for {ticker}: {e}")
        return None


def fetch_universe_fundamentals(use_cache=True):
    """
    Fetch fundamental data for all tickers in the universe.
    Uses cache file on cloud platforms to avoid yfinance rate limiting.
    Falls back to live yfinance fetch if cache not available.

    Args:
        use_cache: if False, skip the cache file and fetch live.
            cache_fundamentals.py passes False — the old code called
            this cache-first, so a local "refresh" re-saved stale
            data with a fresh date.

    Returns:
        dict of {ticker: fundamentals_dict}
    """
    # Try cache first — works on cloud platforms
    cache_path = _cache_path()

    if use_cache and os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            cache = json.load(f)
        results = {k: v["data"] for k, v in cache.items()
                  if k != "_meta"}
        info = get_fundamentals_cache_info()
        cached_date = info["cached_date"] or "unknown"
        print(f"Fundamentals loaded from cache (cached: {cached_date})")
        if info["stale"]:
            print(f"  ⚠️  WARNING: fundamentals cache is "
                  f"{info['age_days']} days old (cached: {cached_date}) "
                  f"— older than the {CACHE_MAX_AGE_DAYS}-day refresh "
                  f"cadence. Fundamental scores may be stale.")
        return results

    # Fall back to live fetch
    print(f"Fetching fundamentals for {len(UNIVERSE)} tickers...\n")

    results = {}
    failed  = []

    for ticker in UNIVERSE.keys():
        data = fetch_fundamentals(ticker)
        if data is not None:
            results[ticker] = data
            print(f"  {ticker:<6} — fetched")
        else:
            failed.append(ticker)

    print(f"\nSuccess: {len(results)}/{len(UNIVERSE)} tickers")
    if failed:
        print(f"Failed:  {failed}")

    return results


def score_fundamentals(fund):
    """
    Score fundamental data 0-100.

    Returns None when there is no data at all (all five scored fields
    None) — callers must treat that as "no measurement", not as a
    number. Before this fix the all-None case scored 49 (half credit
    on every field) while a fetch failure scored 50, and the 1-point
    difference flipped the NEUTRAL/WEAK band. Partial data still
    scores with the per-field half-credit ladder — that ladder is a
    judgment call Kevin has not yet ruled on (see CHANGELOG [2.10]).
    """
    scored_fields = ["revenue_growth", "gross_margin",
                     "operating_margin", "debt_to_equity",
                     "earnings_growth"]
    if all(fund.get(f) is None for f in scored_fields):
        return None

    score = 0
    notes = []

    # Revenue growth (30 points)
    rg = fund.get("revenue_growth")
    if rg is None:
        score += 15
        notes.append("Revenue growth: no data")
    elif rg >= 0.20:
        score += 30
        notes.append(f"Revenue growth: strong ({rg:.1%})")
    elif rg >= 0.10:
        score += 22
        notes.append(f"Revenue growth: moderate ({rg:.1%})")
    elif rg >= 0.0:
        score += 12
        notes.append(f"Revenue growth: low ({rg:.1%})")
    else:
        score += 0
        notes.append(f"Revenue growth: negative ({rg:.1%})")

    # Gross margin (20 points)
    gm = fund.get("gross_margin")
    if gm is None:
        score += 10
        notes.append("Gross margin: no data")
    elif gm >= 0.35:
        score += 20
        notes.append(f"Gross margin: strong ({gm:.1%})")
    elif gm >= 0.20:
        score += 14
        notes.append(f"Gross margin: moderate ({gm:.1%})")
    elif gm >= 0.10:
        score += 7
        notes.append(f"Gross margin: thin ({gm:.1%})")
    else:
        score += 0
        notes.append(f"Gross margin: very thin ({gm:.1%})")

    # Operating margin (20 points)
    om = fund.get("operating_margin")
    if om is None:
        score += 10
        notes.append("Operating margin: no data")
    elif om >= 0.15:
        score += 20
        notes.append(f"Operating margin: strong ({om:.1%})")
    elif om >= 0.08:
        score += 14
        notes.append(f"Operating margin: moderate ({om:.1%})")
    elif om >= 0.0:
        score += 7
        notes.append(f"Operating margin: thin ({om:.1%})")
    else:
        score += 0
        notes.append(f"Operating margin: negative ({om:.1%})")

    # Debt to equity (15 points)
    de = fund.get("debt_to_equity")
    if de is None:
        score += 7
        notes.append("Debt/equity: no data")
    elif de <= 50:
        score += 15
        notes.append(f"Debt/equity: low ({de:.1f})")
    elif de <= 100:
        score += 10
        notes.append(f"Debt/equity: moderate ({de:.1f})")
    elif de <= 200:
        score += 5
        notes.append(f"Debt/equity: elevated ({de:.1f})")
    else:
        score += 0
        notes.append(f"Debt/equity: high ({de:.1f})")

    # Earnings growth (15 points)
    eg = fund.get("earnings_growth")
    if eg is None:
        score += 7
        notes.append("Earnings growth: no data")
    elif eg >= 0.15:
        score += 15
        notes.append(f"Earnings growth: strong ({eg:.1%})")
    elif eg >= 0.05:
        score += 10
        notes.append(f"Earnings growth: moderate ({eg:.1%})")
    elif eg >= 0.0:
        score += 5
        notes.append(f"Earnings growth: low ({eg:.1%})")
    else:
        score += 0
        notes.append(f"Earnings growth: negative ({eg:.1%})")

    return {
        "fundamental_score": min(score, 100),
        "notes"            : notes,
    }


def display_fundamentals(results):
    """Display fundamental data and scores."""
    print("\n--- Fundamental Data ---\n")
    print(
        f"{'Ticker':<6} {'Rev Gr':>8} {'Gr Mgn':>8} "
        f"{'Op Mgn':>8} {'D/E':>8} {'Earn Gr':>8} {'F.Score':>8}"
    )
    print("-" * 65)

    scored = {}
    for ticker, fund in results.items():
        fs = score_fundamentals(fund)
        fscore = f"{fs['fundamental_score']:>8.1f}" if fs is not None else "     N/A"

        rg  = f"{fund['revenue_growth']:.1%}"   if fund['revenue_growth']   is not None else "N/A"
        gm  = f"{fund['gross_margin']:.1%}"     if fund['gross_margin']     is not None else "N/A"
        om  = f"{fund['operating_margin']:.1%}" if fund['operating_margin'] is not None else "N/A"
        de  = f"{fund['debt_to_equity']:.1f}"   if fund['debt_to_equity']   is not None else "N/A"
        eg  = f"{fund['earnings_growth']:.1%}"  if fund['earnings_growth']  is not None else "N/A"

        print(
            f"{ticker:<6} {rg:>8} {gm:>8} "
            f"{om:>8} {de:>8} {eg:>8} "
            f"{fscore}"
        )
        scored[ticker] = fs

    return scored


if __name__ == "__main__":
    results = fetch_universe_fundamentals()
    display_fundamentals(results)