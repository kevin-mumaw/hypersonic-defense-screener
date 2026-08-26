# positions.py
# Manual positions file for Agentic account (••••5038)
# Updated after each trade execution via Claude + Robinhood MCP

POSITIONS = {
    "HWM" : {"shares": 0.405934, "avg_cost": 270.98},
    "HEI" : {"shares": 0.325174, "avg_cost": 338.40},
    "LOAR": {"shares": 1.304726, "avg_cost": 68.98},
    "AXON": {"shares": 0.300347, "avg_cost": 466.13},
    "CW"  : {"shares": 0.080375, "avg_cost": 746.50},
    "ATI" : {"shares": 0.250000, "avg_cost": 220.00},
    "KRMN": {"shares": 0.920979, "avg_cost": 54.29},
    "KTOS": {"shares": 0.828576, "avg_cost": 54.31},
    "PLTR": {"shares": 0.542643, "avg_cost": 165.60},

CASH = 0.00
LAST_UPDATED = "2026-08-26"


if __name__ == "__main__":
    print(f"Positions as of {LAST_UPDATED}")
    print(f"Cash: ${CASH:.2f}\n")
    for ticker, pos in POSITIONS.items():
        print(f"  {ticker:<6} — {pos['shares']:.4f} shares @ ${pos['avg_cost']:.2f}")