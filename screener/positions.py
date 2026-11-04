# positions.py
# Manual positions file for Agentic account (••••5038)
# Updated after each trade execution via Claude + Robinhood MCP

POSITIONS = {
    "HWM" : {"shares": 1.184490, "avg_cost": 244.88},
    "HEI" : {"shares": 0.443226, "avg_cost": 316.23},
    "LOAR": {"shares": 1.304726, "avg_cost": 68.98},
    "AXON": {"shares": 0.300347, "avg_cost": 466.13},
    "CW"  : {"shares": 0.080375, "avg_cost": 746.50},
    "ATI" : {"shares": 0.250000, "avg_cost": 220.00},
    "KRMN": {"shares": 0.920979, "avg_cost": 54.29},
    "KTOS": {"shares": 2.631636, "avg_cost": 45.35},
    "PLTR": {"shares": 1.732506, "avg_cost": 178.87},
}

CASH = 33.79
LAST_UPDATED = "2026-11-03"

# Manual overrides — bypass shock triggers for deliberate positions
# Format: ticker: (reason, expiry_date)
# Expiry date: when to reassess — engine flags again after this date
OVERRIDES = {
       "PLTR": (
       "DELIBERATE_ADD — bought $100 at $167.85 after market drop and earnings, Nov 3. "
       "Review if guidance cut or close below $150.",
       "2026-12-01"),
       
       "HWM": (
       "DELIBERATE_OVERWEIGHT — contrarian thesis buy at discount "
        "after SpaceX/turbine blade noise. Analyst targets $316-350. "
        "Renewed Nov 1. Trim sooner if thesis breaks: guidance cut or "
        "close below $180.",
        "2026-12-01"  # Reassess December 1
    ),
}

# Open WATCH flags — the rebalance engine will not BUY these tickers
# (sells are unaffected). Remove a ticker once the concern is resolved.
WATCH = {
    "KRMN": "Governance watch — CFO departure Aug 2026, J Capital short report",
}
MIN_BUY_SCORE = 55   # shock-low buys need a composite score at or above this


if __name__ == "__main__":
    print(f"Positions as of {LAST_UPDATED}")
    print(f"Cash: ${CASH:.2f}\n")
    for ticker, pos in POSITIONS.items():
        print(f"  {ticker:<6} — {pos['shares']:.4f} shares @ ${pos['avg_cost']:.2f}")