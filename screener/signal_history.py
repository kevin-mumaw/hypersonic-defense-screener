# signal_history.py
# Tracks daily composite scores for all universe tickers
# Saves to data/signal_history.json
# Enables trend analysis — improving vs deteriorating names
# Flags names that have been WEAK for 2+ consecutive weeks

import json
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from universe import UNIVERSE

HISTORY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "data", "signal_history.json"
)


def load_history():
    """Load existing signal history from JSON file."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}


def save_history(history):
    """Save signal history to JSON file."""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def record_daily_scores(scores):
    """
    Record today's composite scores to history.
    
    Args:
        scores: list of score dicts from score_universe()
    """
    today     = date.today().strftime("%Y-%m-%d")
    history   = load_history()

    for s in scores:
        ticker = s["ticker"]
        if ticker not in history:
            history[ticker] = []

        # Avoid duplicate entries for same day
        existing_dates = [entry["date"] for entry in history[ticker]]
        if today not in existing_dates:
            history[ticker].append({
                "date"       : today,
                "composite"  : s["composite"],
                "technical"  : s["technical"],
                "fundamental": s["fundamental"],
                "thesis"     : s["thesis"],
                "signal"     : s["signal"],
                "action"     : s["action"],
            })

    save_history(history)
    print(f"Signal history updated: {today}")
    return history


def get_score_trend(ticker, days=30):
    """
    Get score trend for a ticker over the last N days.
    
    Returns:
        dict with trend analysis
    """
    history = load_history()

    if ticker not in history:
        return None

    entries = history[ticker]

    # Filter to last N days
    cutoff = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = [e for e in entries if e["date"] >= cutoff]

    if len(recent) < 2:
        return {
            "ticker"         : ticker,
            "data_points"    : len(recent),
            "trend"          : "INSUFFICIENT DATA",
            "avg_score"      : recent[0]["composite"] if recent else None,
            "score_change"   : None,
            "consecutive_weak": 0,
        }

    scores      = [e["composite"] for e in recent]
    avg_score   = round(sum(scores) / len(scores), 1)
    first_score = scores[0]
    last_score  = scores[-1]
    score_change = round(last_score - first_score, 1)

    # Trend direction
    if score_change >= 5:
        trend = "IMPROVING"
    elif score_change <= -5:
        trend = "DETERIORATING"
    else:
        trend = "STABLE"

    # Count consecutive WEAK signals
    consecutive_weak = 0
    for entry in reversed(recent):
        if entry["signal"] in ("WEAK", "CRITICAL"):
            consecutive_weak += 1
        else:
            break

    return {
        "ticker"          : ticker,
        "data_points"     : len(recent),
        "trend"           : trend,
        "avg_score"       : avg_score,
        "first_score"     : first_score,
        "last_score"      : last_score,
        "score_change"    : score_change,
        "consecutive_weak": consecutive_weak,
    }


def get_universe_trends(days=30):
    """
    Get score trends for all universe tickers.
    Flags removal candidates and improving names.
    
    Returns:
        dict of trend analysis per ticker
    """
    trends = {}
    removal_candidates = []
    improving_names    = []

    for ticker in UNIVERSE.keys():
        trend = get_score_trend(ticker, days=days)
        if trend:
            trends[ticker] = trend

            # Flag removal candidates — WEAK for 10+ days
            if trend["consecutive_weak"] >= 10:
                removal_candidates.append(ticker)

            # Flag improving names
            if trend["trend"] == "IMPROVING":
                improving_names.append(ticker)

    return {
        "trends"              : trends,
        "removal_candidates"  : removal_candidates,
        "improving_names"     : improving_names,
    }


def generate_trend_report():
    """
    Generate a markdown trend report for the daily briefing.
    """
    today  = date.today().strftime("%B %d, %Y")
    result = get_universe_trends(days=30)
    trends = result["trends"]
    lines  = []

    lines.append("## 📈 30-Day Score Trends")
    lines.append("")

    if not trends:
        lines.append("> Insufficient history — trends available after 2+ trading days.")
        return "\n".join(lines)

    lines.append("| Ticker | Avg Score | Change | Trend | Consec. Weak |")
    lines.append("|--------|----------:|-------:|-------|-------------|")

    for ticker, t in sorted(trends.items(),
                        key=lambda x: x[1].get("score_change") or 0,
                        reverse=True):
        change_str = f"{t['score_change']:+.1f}" if t["score_change"] is not None else "N/A"
        weak_str   = str(t["consecutive_weak"]) if t["consecutive_weak"] > 0 else "—"
        trend_icon = {
            "IMPROVING"        : "⬆️",
            "DETERIORATING"    : "⬇️",
            "STABLE"           : "➡️",
            "INSUFFICIENT DATA": "❓",
        }.get(t["trend"], "❓")

        lines.append(
            f"| {ticker} "
            f"| {t['avg_score']} "
            f"| {change_str} "
            f"| {trend_icon} {t['trend']} "
            f"| {weak_str} |"
        )

    if result["removal_candidates"]:
        lines.append("")
        lines.append("### ⚠️ Removal Candidates (WEAK 10+ consecutive days)")
        for ticker in result["removal_candidates"]:
            lines.append(f"- **{ticker}** — review thesis fit immediately")

    if result["improving_names"]:
        lines.append("")
        lines.append("### ✅ Improving Names")
        for ticker in result["improving_names"]:
            lines.append(f"- **{ticker}**")

    return "\n".join(lines)


if __name__ == "__main__":
    from score import score_universe
    print("Recording today's scores to signal history...")
    scores  = score_universe()
    history = record_daily_scores(scores)
    print(f"History now contains {len(history)} tickers")
    print()
    print(generate_trend_report())