# report.py
# Generates human-readable narrative summary of screener output
# Designed to read like a morning briefing, not a data table
# Output format suitable for Autopilot Pilot documentation

from datetime import date
from score import score_universe
from signals import calculate_universe_signals


def get_universe_posture(scores):
    """
    Determine overall universe posture based on
    distribution of composite scores.
    """
    strong  = sum(1 for s in scores if s["composite"] >= 75)
    neutral = sum(1 for s in scores if 50 <= s["composite"] < 75)
    weak    = sum(1 for s in scores if s["composite"] < 50)
    total   = len(scores)

    if strong >= total * 0.5:
        return "BULLISH"
    elif weak >= total * 0.5:
        return "BEARISH"
    elif strong >= total * 0.3:
        return "CAUTIOUSLY BULLISH"
    elif weak >= total * 0.3:
        return "CAUTIOUSLY BEARISH"
    else:
        return "MIXED"


def generate_signal_groups(signals):
    """
    Group tickers by signal pattern for narrative generation.
    Returns dict of pattern -> list of tickers.
    """
    groups = {
        "overbought_bullish" : [],
        "bullish_neutral"    : [],
        "bullish_volume"     : [],
        "mixed"              : [],
        "bearish"            : [],
        "oversold"           : [],
    }

    for ticker, s in signals.items():
        trend = s["trend"]
        rsi   = s["rsi"]
        vol   = s["vol_confirmed"]

        if trend == "BULLISH" and rsi >= 70:
            groups["overbought_bullish"].append(ticker)
        elif trend == "BULLISH" and vol:
            groups["bullish_volume"].append(ticker)
        elif trend == "BULLISH":
            groups["bullish_neutral"].append(ticker)
        elif trend == "BEARISH":
            groups["bearish"].append(ticker)
        elif rsi <= 30:
            groups["oversold"].append(ticker)
        else:
            groups["mixed"].append(ticker)

    return groups


def generate_narrative(scores, signals):
    """
    Generate plain English narrative summary.
    Grouped by signal pattern, one bullet per group.
    """
    posture = get_universe_posture(scores)
    groups  = generate_signal_groups(signals)
    today   = date.today().strftime("%B %d, %Y")

    lines = []
    lines.append("=" * 55)
    lines.append(f"  Hypersonic Defense Screener — Daily Briefing")
    lines.append(f"  {today}")
    lines.append("=" * 55)
    lines.append(f"\nUNIVERSE POSTURE: {posture}\n")

    lines.append("Immediate Observations:\n")

    if groups["overbought_bullish"]:
        tickers = ", ".join(groups["overbought_bullish"])
        lines.append(
            f"  * {tickers} — Overbought (RSI 70+), Bullish trend. "
            f"Strong momentum but extended — not ideal entry points right now."
        )

    if groups["bullish_volume"]:
        tickers = ", ".join(groups["bullish_volume"])
        lines.append(
            f"  * {tickers} — Bullish trend with volume confirmation. "
            f"Strongest technical setup in the universe today."
        )

    if groups["bullish_neutral"]:
        tickers = ", ".join(groups["bullish_neutral"])
        lines.append(
            f"  * {tickers} — Bullish trend, neutral RSI. "
            f"Cleaner setups — momentum building without being extended."
        )

    if groups["mixed"]:
        tickers = ", ".join(groups["mixed"])
        lines.append(
            f"  * {tickers} — Mixed signals, neither clearly "
            f"bullish nor bearish. No action bias."
        )

    if groups["bearish"]:
        tickers = ", ".join(groups["bearish"])
        lines.append(
            f"  * {tickers} — Bearish trend, trading below key "
            f"moving averages. Warrants caution — review thesis fit."
        )

    if groups["oversold"]:
        tickers = ", ".join(groups["oversold"])
        lines.append(
            f"  * {tickers} — Oversold (RSI 30 or below). "
            f"Potential reversal candidate — monitor closely."
        )

    lines.append("\n--- Ranked Scores ---\n")
    lines.append(
        f"  {'Rank':<5} {'Ticker':<6} {'Score':>6} "
        f"{'Signal':<10} Action"
    )
    lines.append("  " + "-" * 50)

    for i, s in enumerate(scores, 1):
        lines.append(
            f"  {i:<5} "
            f"{s['ticker']:<6} "
            f"{s['composite']:>6.1f} "
            f"{s['signal']:<10} "
            f"{s['action']}"
        )

    lines.append("\n" + "=" * 55)
    lines.append(
        "  Note: Fundamental and thesis scores are Phase 1\n"
        "  placeholders. Rankings driven by technical signals.\n"
        "  Scores will improve as fundamentals are integrated."
    )
    lines.append("=" * 55)

    return "\n".join(lines)


def run_report():
    """
    Run full screener and print narrative report.
    """
    scores  = score_universe()
    signals = calculate_universe_signals(period="6mo")
    report  = generate_narrative(scores, signals)

    print("\n\n")
    print(report)
    return report


if __name__ == "__main__":
    run_report()