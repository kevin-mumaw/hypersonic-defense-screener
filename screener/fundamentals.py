# fundamentals.py
# Fetches and scores fundamental data for all universe tickers
# Phase 2 Part A: Automated via yfinance
# Phase 2 Part B: Manual inputs for backlog and defense revenue mix
# Data limitations documented honestly per SCREENER_SPEC.md

import yfinance as yf
import pandas as pd
from universe import UNIVERSE


def fetch_fundamentals(ticker):
    """
    Fetch fundamental data for a single ticker via yfinance.
    
    Returns:
        dict of fundamental metrics or None if fetch fails
    """
    try:
        stock = yf.Ticker(ticker)
        info  = stock.info

        # Revenue growth YoY
        revenue_growth = info.get("revenueGrowth", None)

        # Margins
        gross_margin     = info.get("grossMargins", None)
        operating_margin = info.get("operatingMargins", None)
        profit_margin    = info.get("profitMargins", None)

        # Balance sheet health
        debt_to_equity = info.get("debtToEquity", None)

        # Revenue (trailing twelve months)
        total_revenue = info.get("totalRevenue", None)

        # Earnings growth
        earnings_growth = info.get("earningsGrowth", None)

        # Return on equity
        roe = info.get("returnOnEquity", None)

        return {
            "ticker"          : ticker,
            "revenue_growth"  : revenue_growth,
            "gross_margin"    : gross_margin,
            "operating_margin": operating_margin,
            "profit_margin"   : profit_margin,
            "debt_to_equity"  : debt_to_equity,
            "total_revenue"   : total_revenue,
            "earnings_growth" : earnings_growth,
            "roe"             : roe,
        }

    except Exception as e:
        print(f"  ERROR fetching fundamentals for {ticker}: {e}")
        return None


def fetch_universe_fundamentals():
    """
    Fetch fundamental data for all tickers in the universe.
    
    Returns:
        dict of {ticker: fundamentals_dict}
    """
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
    
    Scoring logic:
    - Revenue growth  : 30 points
    - Gross margin    : 20 points
    - Operating margin: 20 points
    - Debt to equity  : 15 points
    - Earnings growth : 15 points
    
    None values score neutral (50% of available points)
    to avoid penalizing data gaps unfairly.
    """
    score = 0
    notes = []

    # Revenue growth (30 points)
    rg = fund.get("revenue_growth")
    if rg is None:
        score += 15  # Neutral — no data
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

    # Debt to equity (15 points) — lower is better
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
    """
    Display fundamental data and scores in a readable table.
    """
    print("\n--- Fundamental Data ---\n")
    print(
        f"{'Ticker':<6} {'Rev Gr':>8} {'Gr Mgn':>8} "
        f"{'Op Mgn':>8} {'D/E':>8} {'Earn Gr':>8} {'F.Score':>8}"
    )
    print("-" * 65)

    scored = {}
    for ticker, fund in results.items():
        fs = score_fundamentals(fund)

        rg  = f"{fund['revenue_growth']:.1%}"  if fund['revenue_growth']  is not None else "N/A"
        gm  = f"{fund['gross_margin']:.1%}"    if fund['gross_margin']    is not None else "N/A"
        om  = f"{fund['operating_margin']:.1%}" if fund['operating_margin'] is not None else "N/A"
        de  = f"{fund['debt_to_equity']:.1f}"  if fund['debt_to_equity']  is not None else "N/A"
        eg  = f"{fund['earnings_growth']:.1%}" if fund['earnings_growth'] is not None else "N/A"

        print(
            f"{ticker:<6} {rg:>8} {gm:>8} "
            f"{om:>8} {de:>8} {eg:>8} "
            f"{fs['fundamental_score']:>8.1f}"
        )

        scored[ticker] = fs

    return scored


if __name__ == "__main__":
    results = fetch_universe_fundamentals()
    scored  = display_fundamentals(results)

    print("\n--- Fundamental Score Notes ---\n")
    for ticker, fs in scored.items():
        print(f"{ticker}:")
        for note in fs["notes"]:
            print(f"  - {note}")
        print()