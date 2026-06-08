# backtest.py
# Backtests technical signal logic against historical price data
# IMPORTANT LIMITATIONS (documented honestly):
#   - Technical signals only — fundamental and thesis not backtestable
#     with free data due to point-in-time data limitations
#   - Survivorship bias — all current universe tickers survived
#   - No transaction costs modeled
#   - No slippage modeled
#   - Past performance does not predict future results
# Output: markdown report saved to backtest/ folder

import sys
import os
import pandas as pd
import numpy as np
from datetime import date

# Add screener folder to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'screener'))

from data import fetch_price_data
from universe import UNIVERSE


def calculate_rsi(series, period=14):
    """Calculate RSI for a price series."""
    delta    = series.diff()
    gain     = delta.where(delta > 0, 0.0)
    loss     = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs       = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_technical_score(close, volume, idx):
    """
    Calculate technical score at a specific index position.
    Mirrors logic in signals.py and score.py.
    """
    if idx < 50:
        return None  # Not enough data for MA50

    window = close.iloc[:idx+1]
    vol_window = volume.iloc[:idx+1]

    ma20 = window.rolling(20).mean().iloc[-1]
    ma50 = window.rolling(50).mean().iloc[-1]
    rsi  = calculate_rsi(window).iloc[-1]
    vol_avg20 = vol_window.rolling(20).mean().iloc[-1]

    price = window.iloc[-1]
    vol   = vol_window.iloc[-1]

    above_ma20   = price > ma20
    above_ma50   = price > ma50
    ma20_vs_ma50 = ma20 > ma50
    vol_confirmed = vol > vol_avg20

    # Trend
    if above_ma20 and above_ma50:
        trend = "BULLISH"
    elif not above_ma20 and not above_ma50:
        trend = "BEARISH"
    else:
        trend = "MIXED"

    # Score (mirrors score.py)
    score = 0

    if trend == "BULLISH":
        score += 40
    elif trend == "MIXED":
        score += 20

    if 40 <= rsi <= 60:
        score += 30
    elif 30 <= rsi < 40 or 60 < rsi <= 70:
        score += 15
    elif rsi > 70:
        score += 5
    elif rsi < 30:
        score += 10

    if ma20_vs_ma50:
        score += 20

    if vol_confirmed:
        score += 10

    return min(score, 100)


def backtest_ticker(ticker, period="2y", buy_threshold=60, sell_threshold=45):
    """
    Backtest technical signal logic for a single ticker.

    Args:
        ticker         : stock symbol
        period         : historical lookback period
        buy_threshold  : technical score to trigger buy signal
        sell_threshold : technical score to trigger sell signal

    Returns:
        dict of backtest results
    """
    df = fetch_price_data(ticker, period=period)
    if df is None or len(df) < 60:
        return None

    close  = df["Close"].squeeze()
    volume = df["Volume"].squeeze()

    trades     = []
    position   = None  # None = no position, dict = open position
    scores     = []

    for i in range(50, len(close)):
        score = calculate_technical_score(close, volume, i)
        if score is None:
            continue

        scores.append(score)
        price = close.iloc[i]
        dt    = close.index[i]

        # Buy signal
        if position is None and score >= buy_threshold:
            position = {
                "entry_date" : dt,
                "entry_price": price,
                "entry_score": score,
            }

        # Sell signal
        elif position is not None and score <= sell_threshold:
            exit_price  = price
            pct_return  = (exit_price - position["entry_price"]) / position["entry_price"] * 100

            trades.append({
                "ticker"      : ticker,
                "entry_date"  : position["entry_date"].strftime("%Y-%m-%d"),
                "exit_date"   : dt.strftime("%Y-%m-%d"),
                "entry_price" : round(position["entry_price"], 2),
                "exit_price"  : round(exit_price, 2),
                "return_pct"  : round(pct_return, 2),
                "win"         : pct_return > 0,
            })
            position = None

    # Close any open position at last price
    if position is not None:
        exit_price = close.iloc[-1]
        pct_return = (exit_price - position["entry_price"]) / position["entry_price"] * 100
        trades.append({
            "ticker"      : ticker,
            "entry_date"  : position["entry_date"].strftime("%Y-%m-%d"),
            "exit_date"   : "OPEN",
            "entry_price" : round(position["entry_price"], 2),
            "exit_price"  : round(exit_price, 2),
            "return_pct"  : round(pct_return, 2),
            "win"         : pct_return > 0,
        })

    # Summary stats
    if not trades:
        return {
            "ticker"      : ticker,
            "trades"      : 0,
            "win_rate"    : None,
            "avg_return"  : None,
            "best_trade"  : None,
            "worst_trade" : None,
            "total_return": None,
            "trade_log"   : [],
        }

    closed = [t for t in trades if t["exit_date"] != "OPEN"]
    wins   = [t for t in closed if t["win"]]

    return {
        "ticker"      : ticker,
        "trades"      : len(trades),
        "win_rate"    : round(len(wins) / len(closed) * 100, 1) if closed else None,
        "avg_return"  : round(np.mean([t["return_pct"] for t in closed]), 2) if closed else None,
        "best_trade"  : round(max([t["return_pct"] for t in closed]), 2) if closed else None,
        "worst_trade" : round(min([t["return_pct"] for t in closed]), 2) if closed else None,
        "total_return": round(sum([t["return_pct"] for t in closed]), 2) if closed else None,
        "trade_log"   : trades,
    }


def backtest_universe(period="2y", buy_threshold=60, sell_threshold=45):
    """
    Run backtest for all universe tickers.
    """
    print(f"Running backtest...")
    print(f"Period: {period} | Buy threshold: {buy_threshold} | Sell threshold: {sell_threshold}\n")

    results = {}
    for ticker in UNIVERSE.keys():
        result = backtest_ticker(ticker, period=period,
                                buy_threshold=buy_threshold,
                                sell_threshold=sell_threshold)
        if result:
            results[ticker] = result
            trades    = result["trades"]
            win_rate  = f"{result['win_rate']}%" if result["win_rate"] is not None else "N/A"
            avg_ret   = f"{result['avg_return']}%" if result["avg_return"] is not None else "N/A"
            print(f"  {ticker:<6} — {trades} trades | Win rate: {win_rate} | Avg return: {avg_ret}")

    return results


def generate_backtest_report(results, period, buy_threshold, sell_threshold):
    """
    Generate markdown backtest report.
    """
    today = date.today().strftime("%B %d, %Y")
    lines = []

    lines.append("# Hypersonic Defense Screener — Backtest Report")
    lines.append(f"## {today}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Parameters")
    lines.append("")
    lines.append(f"| Parameter | Value |")
    lines.append(f"|-----------|-------|")
    lines.append(f"| Period | {period} |")
    lines.append(f"| Buy threshold (technical score) | {buy_threshold} |")
    lines.append(f"| Sell threshold (technical score) | {sell_threshold} |")
    lines.append(f"| Signal type | Technical only |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Honest Limitations")
    lines.append("")
    lines.append("> - **Technical signals only** — fundamental and thesis")
    lines.append(">   components cannot be backtested with free data")
    lines.append("> - **Survivorship bias** — all tickers survived to today")
    lines.append("> - **No transaction costs or slippage modeled**")
    lines.append("> - **Past performance does not predict future results**")
    lines.append("> - Results should be used to validate signal logic only,")
    lines.append(">   not to project future returns")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Summary Results")
    lines.append("")
    lines.append("| Ticker | Trades | Win Rate | Avg Return | Best | Worst | Total |")
    lines.append("|--------|-------:|---------:|-----------:|-----:|------:|------:|")

    for ticker, r in sorted(results.items(),
                            key=lambda x: x[1]["win_rate"] or 0,
                            reverse=True):
        wr  = f"{r['win_rate']}%"  if r["win_rate"]    is not None else "N/A"
        ar  = f"{r['avg_return']}%" if r["avg_return"]  is not None else "N/A"
        bt  = f"{r['best_trade']}%" if r["best_trade"]  is not None else "N/A"
        wt  = f"{r['worst_trade']}%" if r["worst_trade"] is not None else "N/A"
        tr  = f"{r['total_return']}%" if r["total_return"] is not None else "N/A"

        lines.append(
            f"| {ticker} | {r['trades']} | {wr} | {ar} | {bt} | {wt} | {tr} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Trade Logs")
    lines.append("")

    for ticker, r in results.items():
        if not r["trade_log"]:
            continue
        lines.append(f"### {ticker}")
        lines.append("")
        lines.append("| Entry Date | Exit Date | Entry Price | Exit Price | Return |")
        lines.append("|------------|-----------|------------:|-----------:|-------:|")
        for t in r["trade_log"]:
            lines.append(
                f"| {t['entry_date']} "
                f"| {t['exit_date']} "
                f"| ${t['entry_price']} "
                f"| ${t['exit_price']} "
                f"| {t['return_pct']}% |"
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"*Generated by Hypersonic Defense Screener — {today}*")

    return "\n".join(lines)


def save_backtest_report(markdown):
    """Save backtest report to backtest folder."""
    today    = date.today().strftime("%Y-%m-%d")
    filename = f"backtest_{today}.md"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath   = os.path.join(script_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"\nReport saved: backtest/{filename}")
    return filepath


if __name__ == "__main__":
    results  = backtest_universe(period="2y",
                                 buy_threshold=60,
                                 sell_threshold=45)
    markdown = generate_backtest_report(results, "2y", 60, 45)
    save_backtest_report(markdown)

    print("\n")
    print(markdown)