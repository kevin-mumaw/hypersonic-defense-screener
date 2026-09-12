# drift_history.py
# Tracks daily position weights to enforce the 30-day drift buffer rule
# Saves to data/drift_history.json
# Rebalancing engine reads this to determine if drift has persisted 30+ days
# Shock triggers (13.5%/6.5%) still fire immediately regardless

import json
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DRIFT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "data", "drift_history.json"
)

DRIFT_THRESHOLD = 0.020   # 2% drift threshold
DRIFT_DAYS      = 30      # Days before drift triggers rebalance


def load_drift_history():
    """Load existing drift history from JSON file."""
    if os.path.exists(DRIFT_FILE):
        with open(DRIFT_FILE, "r") as f:
            return json.load(f)
    return {}


def save_drift_history(history):
    """Save drift history to JSON file."""
    os.makedirs(os.path.dirname(DRIFT_FILE), exist_ok=True)
    with open(DRIFT_FILE, "w") as f:
        json.dump(history, f, indent=2)


def record_daily_weights(positions_with_value, target_weights):
    """
    Record today's position weights and drift status.

    Args:
        positions_with_value : dict from rebalance.py
        target_weights       : dict of {ticker: target_pct} from rebalance.py
    """
    today   = date.today().strftime("%Y-%m-%d")
    history = load_drift_history()

    for ticker, data in positions_with_value.items():
        current_pct = data["current_pct"] * 100
        target_pct  = target_weights.get(ticker, 0)
        deviation   = current_pct - target_pct
        in_drift    = abs(deviation) > (DRIFT_THRESHOLD * 100)

        if ticker not in history:
            history[ticker] = []

        # Avoid duplicate entries for same day
        existing_dates = [entry["date"] for entry in history[ticker]]
        if today not in existing_dates:
            history[ticker].append({
                "date"       : today,
                "current_pct": round(current_pct, 2),
                "target_pct" : round(target_pct, 2),
                "deviation"  : round(deviation, 2),
                "in_drift"   : in_drift,
            })

    save_drift_history(history)
    print(f"Drift history updated: {today}")
    return history


def get_consecutive_drift_days(ticker):
    """
    Count how many consecutive days a ticker has been in drift.

    Returns:
        int — number of consecutive days in drift (0 if not drifting)
    """
    history = load_drift_history()

    if ticker not in history:
        return 0

    entries = sorted(history[ticker], key=lambda x: x["date"], reverse=True)

    consecutive = 0
    for entry in entries:
        if entry["in_drift"]:
            consecutive += 1
        else:
            break

    return consecutive


def get_drift_status(positions_with_value, target_weights):
    """
    Get drift status for all positions.
    Distinguishes between:
    - Shock triggers (immediate action regardless of time)
    - Qualified drift (30+ consecutive days, queue for rebalance)
    - Recent drift (< 30 days, monitor only)

    Returns:
        dict with shock_triggers, qualified_drift, recent_drift
    """
    from rebalance import SHOCK_HIGH, SHOCK_LOW

    shock_triggers   = []
    qualified_drift  = []
    recent_drift     = []

    for ticker, data in positions_with_value.items():
        current_pct = data["current_pct"]
        target_pct  = target_weights.get(ticker, 0) / 100
        deviation   = current_pct - target_pct
        consec_days = get_consecutive_drift_days(ticker)

        # Shock triggers — immediate regardless of time
        if current_pct > SHOCK_HIGH:
            shock_triggers.append({
                "ticker"     : ticker,
                "type"       : "SHOCK HIGH",
                "current_pct": round(current_pct * 100, 1),
                "target_pct" : round(target_pct * 100, 1),
                "deviation"  : round(deviation * 100, 1),
                "days"       : consec_days,
            })
        elif current_pct < SHOCK_LOW and current_pct > 0:
            shock_triggers.append({
                "ticker"     : ticker,
                "type"       : "SHOCK LOW",
                "current_pct": round(current_pct * 100, 1),
                "target_pct" : round(target_pct * 100, 1),
                "deviation"  : round(deviation * 100, 1),
                "days"       : consec_days,
            })

        # Drift conditions
        elif abs(deviation) > DRIFT_THRESHOLD:
            entry = {
                "ticker"     : ticker,
                "current_pct": round(current_pct * 100, 1),
                "target_pct" : round(target_pct * 100, 1),
                "deviation"  : round(deviation * 100, 1),
                "days"       : consec_days,
                "action"     : "TRIM" if deviation > 0 else "ADD",
            }
            if consec_days >= DRIFT_DAYS:
                qualified_drift.append(entry)
            else:
                recent_drift.append(entry)

    return {
        "shock_triggers" : shock_triggers,
        "qualified_drift": qualified_drift,
        "recent_drift"   : recent_drift,
    }


def generate_drift_report(drift_status):
    """
    Generate markdown drift status report.
    """
    today = date.today().strftime("%B %d, %Y")
    lines = []

    lines.append("## ⚖️ Drift Status Report")
    lines.append(f"*{today} — 30-day buffer enforced*")
    lines.append("")

    # Shock triggers
    lines.append("### ⚠️ Shock Triggers (Immediate — No Buffer)")
    if drift_status["shock_triggers"]:
        lines.append("")
        lines.append("| Ticker | Type | Current % | Target % | Deviation | Days |")
        lines.append("|--------|------|----------:|---------:|----------:|-----:|")
        for t in drift_status["shock_triggers"]:
            lines.append(
                f"| {t['ticker']} | {t['type']} | "
                f"{t['current_pct']}% | {t['target_pct']}% | "
                f"{t['deviation']:+.1f}% | {t['days']} |"
            )
    else:
        lines.append("> ✅ No shock triggers.")
    lines.append("")

    # Qualified drift
    lines.append("### 🔄 Qualified Drift (30+ Days — Queue for Rebalance)")
    if drift_status["qualified_drift"]:
        lines.append("")
        lines.append("| Ticker | Current % | Target % | Deviation | Days | Action |")
        lines.append("|--------|----------:|---------:|----------:|-----:|--------|")
        for d in drift_status["qualified_drift"]:
            lines.append(
                f"| {d['ticker']} | {d['current_pct']}% | "
                f"{d['target_pct']}% | {d['deviation']:+.1f}% | "
                f"{d['days']} | {d['action']} |"
            )
    else:
        lines.append("> ✅ No positions have drifted for 30+ consecutive days.")
    lines.append("")

    # Recent drift
    lines.append("### 👀 Recent Drift (< 30 Days — Monitor Only)")
    if drift_status["recent_drift"]:
        lines.append("")
        lines.append("| Ticker | Current % | Target % | Deviation | Days | Action |")
        lines.append("|--------|----------:|---------:|----------:|-----:|--------|")
        for d in drift_status["recent_drift"]:
            lines.append(
                f"| {d['ticker']} | {d['current_pct']}% | "
                f"{d['target_pct']}% | {d['deviation']:+.1f}% | "
                f"{d['days']} | Monitor — {d['days']}/{DRIFT_DAYS} days |"
            )
    else:
        lines.append("> ✅ No recent drift conditions.")

    return "\n".join(lines)


if __name__ == "__main__":
    from rebalance import calculate_portfolio_value, calculate_deployed_capital
    from rebalance import normalize_weights, get_current_prices
    from score import score_universe
    from positions import POSITIONS

    print("Running drift history tracker...")

    prices           = get_current_prices()
    portfolio_value  = calculate_portfolio_value(prices)
    deployed, _      = calculate_deployed_capital(portfolio_value)
    scores           = score_universe()
    target_weights   = normalize_weights(scores)

    positions_with_value = {}
    for ticker, pos in POSITIONS.items():
        price        = prices.get(ticker, 0)
        market_value = pos["shares"] * price
        current_pct  = market_value / portfolio_value if portfolio_value > 0 else 0

        positions_with_value[ticker] = {
            "shares"      : pos["shares"],
            "avg_cost"    : pos["avg_cost"],
            "price"       : price,
            "market_value": round(market_value, 2),
            "current_pct" : current_pct,
        }

    record_daily_weights(positions_with_value, target_weights)
    drift_status = get_drift_status(positions_with_value, target_weights)
    print(generate_drift_report(drift_status))