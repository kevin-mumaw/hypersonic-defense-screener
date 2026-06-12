# cache_fundamentals.py
# Run this locally to cache fundamental data to JSON
# Commit the output file to GitHub
# Dashboard reads from cache on cloud — no yfinance needed

import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fundamentals import fetch_universe_fundamentals, score_fundamentals

def run_cache():
    print("Fetching fundamentals and caching to JSON...")
    
    raw_data = fetch_universe_fundamentals()
    
    # Build cache with scores
    cache = {}
    for ticker, fund in raw_data.items():
        scored = score_fundamentals(fund)
        cache[ticker] = {
            "data" : fund,
            "score": scored["fundamental_score"],
            "notes": scored["notes"],
        }
        print(f"  {ticker:<6} — score: {scored['fundamental_score']}")
    
    # Add metadata
    cache["_meta"] = {
        "cached_date": date.today().strftime("%Y-%m-%d"),
        "ticker_count": len(raw_data),
    }
    
    # Save to file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root  = os.path.dirname(script_dir)
    cache_dir  = os.path.join(repo_root, "data")
    os.makedirs(cache_dir, exist_ok=True)
    
    filepath = os.path.join(cache_dir, "fundamentals_cache.json")
    with open(filepath, "w") as f:
        json.dump(cache, f, indent=2, default=str)
    
    print(f"\nCache saved: data/fundamentals_cache.json")
    print(f"Cached {len(raw_data)} tickers on {date.today()}")
    return cache

if __name__ == "__main__":
    run_cache()