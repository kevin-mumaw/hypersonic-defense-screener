# report.py
# Generates human-readable narrative summary of screener output
# Output: markdown format, saved to logs/briefing_YYYY-MM-DD.md
# Also prints to terminal for quick reference
# Designed to read like a morning briefing, not a data table

from datetime import date
from score import score_universe
from signals import calculate_universe_signals
import os


def get_universe_posture(scores):
    """
    Determine overall universe posture based on
    distribution of composite scores.
    """
    strong  = sum(1 for s in scores if s["composite"] >= 75)
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
    """
    groups = {
        "overbought_bullish" : [],
        "bullish_volume"     : [],
        "bullish_neutral"    : [],
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


def generate_markdown(scores, signals):
    """
    Generate markdown formatted narrative report.
    """
    posture = get_universe_posture(scores)
    groups  = generate_signal_groups(signals)
    today   = date.today().strftime("%B %d, %Y")

    lines = []

    # Header
    lines.append("# Hypersonic Defense Screener")
    lines.append(f"## Daily Briefing — {today}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Universe posture
    lines.append(f"## Universe Posture: {posture}")
    lines.append("")

    # Narrative
    lines.append("## Immediate Observations")
    lines.append("")

    if groups["overbought_bullish"]:
        tickers = ", ".join(groups["overbought_bullish"])
        lines.append(
            f"- **{tickers}** — Overbought (RSI 70+), Bullish trend. "
            f"Strong momentum but extended — not ideal entry points right now."
        )

    if groups["bullish_volume"]:
        tickers = ", ".join(groups["bullish_volume"])
        lines.append(
            f"- **{tickers}** — Bullish trend with volume confirmation. "
            f"Strongest technical setup in the universe today."
        )

    if groups["bullish_neutral"]:
        tickers = ", ".join(groups["bullish_neutral"])
        lines.append(
            f"- **{tickers}** — Bullish trend, neutral RSI. "
            f"Cleaner setups — momentum building without being extended."
        )

    if groups["mixed"]:
        tickers = ", ".join(groups["mixed"])
        lines.append(
            f"- **{tickers}** — Mixed signals, neither clearly "
            f"bullish nor bearish. No action bias."
        )

    if groups["bearish"]:
        tickers = ", ".join(groups["bearish"])
        lines.append(
            f"- **{tickers}** — Bearish trend, trading below key "
            f"moving averages. Warrants caution — review thesis fit."
        )

    if groups["oversold"]:
        tickers = ", ".join(groups["oversold"])
        lines.append(
            f"- **{tickers}** — Oversold (RSI 30 or below). "
            f"Potential reversal candidate — monitor closely."
        )

    lines.append("")
    lines.append("---")
    lines.append("")

    # Signals table
    lines.append("## Technical Signals")
    lines.append("")
    lines.append("| Ticker | Close | MA20 | MA50 | RSI | RSI Signal | Trend | Vol Confirmed |")
    lines.append("|--------|------:|-----:|-----:|----:|------------|-------|---------------|")

    for ticker, s in signals.items():
        lines.append(
            f"| {ticker} "
            f"| ${s['close']:,.2f} "
            f"| ${s['ma20']:,.2f} "
            f"| ${s['ma50']:,.2f} "
            f"| {s['rsi']:.1f} "
            f"| {s['rsi_signal']} "
            f"| {s['trend']} "
            f"| {'YES' if s['vol_confirmed'] else 'NO'} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")

    # Scores table
    lines.append("## Composite Scores")
    lines.append("")
    lines.append("| Rank | Ticker | Technical | Fundamental | Thesis | Score | Signal | Action |")
    lines.append("|------|--------|----------:|------------:|-------:|------:|--------|--------|")

    for i, s in enumerate(scores, 1):
        lines.append(
            f"| {i} "
            f"| {s['ticker']} "
            f"| {s['technical']:.1f} "
            f"| {s['fundamental']:.1f} "
            f"| {s['thesis']:.1f} "
            f"| {s['composite']:.1f} "
            f"| {s['signal']} "
            f"| {s['action']} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    # Gap flags
    gap_flags = [
        (s["ticker"], signals[s["ticker"]].get("gap_flag"))
        for s in scores
        if signals.get(s["ticker"], {}).get("gap_flag")
    ]

    if gap_flags:
        lines.append("## ⚠️ Gap Alerts")
        lines.append("")
        for ticker, flag in gap_flags:
            lines.append(f"- **{ticker}** — {flag}")
        lines.append("")
        lines.append("---")
        lines.append("")
    # Notes
    lines.append("## Notes")
    lines.append("")
    lines.append(
        "> **Phase 2 Update:** Fundamental scores now reflect real data "
        "including revenue growth, gross margin, operating margin, "
        "debt/equity, and earnings growth via yfinance. "
        "Thesis scores are manually set per investment thesis alignment. "
        "Phase 3 will incorporate contract wins, program milestones, "
        "and defense revenue mix."
    )
    lines.append("")
    lines.append(
        "> This report is for personal research purposes only. "
        "Nothing here constitutes financial advice."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        f"*Generated by Hypersonic Defense Screener — {today}*"
    )

    return "\n".join(lines)


def save_report(markdown):
    """
    Save markdown report to logs folder with dated filename.
    """
    today    = date.today().strftime("%Y-%m-%d")
    filename = f"briefing_{today}.md"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root  = os.path.dirname(script_dir)
    logs_dir   = os.path.join(repo_root, "logs")
    filepath   = os.path.join(logs_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"Report saved: logs/{filename}")
    return filepath


def run_report():
    """
    Run full screener and generate markdown report.
    """
    scores   = score_universe()
    signals  = calculate_universe_signals(period="6mo")
    markdown = generate_markdown(scores, signals)

    save_report(markdown)

    print("\n\n")
    print(markdown)

    return markdown


if __name__ == "__main__":
    run_report()