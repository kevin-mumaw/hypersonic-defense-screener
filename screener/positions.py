# positions.py
# Manual positions file for Agentic account (••••5038)
# Updated after each trade execution via Claude + Robinhood MCP
# Dashboard reads this file to show real holdings
# This is NOT live-synced — update manually after trades

POSITIONS = {
    "HWM": {
        "shares"   : 0.405934,
        "avg_cost" : 270.98,
    },
    "HEI": {
        "shares"   : 0.325059,
        "avg_cost" : 338.40,
    },
    "LOAR": {
        "shares"   : 1.304726,
        "avg_cost" : 68.98,
    },
    "AXON": {
        "shares"   : 0.200570,
        "avg_cost" : 448.72,
    },
}

CASH = 100.00

LAST_UPDATED = "2026-06-17"


if __name__ == "__main__":
    print(f"Positions as of {LAST_UPDATED}")
    print(f"Cash: ${CASH:.2f}\n")
    for ticker, pos in POSITIONS.items():
        print(f"  {ticker:<6} — {pos['shares']:.4f} shares @ ${pos['avg_cost']:.2f}")