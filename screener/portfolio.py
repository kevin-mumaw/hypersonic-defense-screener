# portfolio.py
# Portfolio tracker for Robinhood Agentic account
# Shows positions alongside current screener scores
# Flags misalignment between holdings and signals
# Agentic account only (5038) — main portfolio tracked separately

import os
import sys
import requests
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from universe import UNIVERSE
from score import score_universe

# --- Configuration ---

AGENTIC_ACCOUNT = "5038"  # Last 4 of Agentic account


# --- Position Data ---

def get_agentic_positions():
    """
    Fetch current positions from Robinhood Agentic account.
    Returns list of position dicts.
    
    Note: This is called from the dashboard which has
    Robinhood MCP access. For standalone use, positions
    must be passed in manually.
    """
    # Placeholder — populated by dashboard via Robinhood MCP
    return []


def build_portfolio_view(positions, scores):
    """
    Build portfolio view combining positions with screener scores.
    
    Args:
        positions : list of dicts with ticker, shares, avg_cost, current_price
        scores    : list of score dicts from score_universe()
    
    Returns:
        dict with portfolio analysis
    """
    # Build score lookup
    score_lookup = {s["ticker"]: s for s in scores}

    # Analyze each position
    portfolio = []
    total_value = sum(
        p.get("shares", 0) * p.get("current_price", 0)
        for p in positions
    )

    for pos in positions:
        ticker        = pos.get("ticker", "")
        shares        = pos.get("shares", 0)
        avg_cost      = pos.get("avg_cost", 0)
        current_price = pos.get("current_price", 0)
        market_value  = shares * current_price
        gain_loss_pct = ((current_price - avg_cost) / avg_cost * 100
                        if avg_cost > 0 else 0)
        weight        = (market_value / total_value * 100
                        if total_value > 0 else 0)

        # Get screener score
        score_data = score_lookup.get(ticker, {})
        score      = score_data.get("composite", None)
        signal     = score_data.get("signal", "NOT IN UNIVERSE")
        action     = score_data.get("action", "Research required")

        # Alignment flag
        if signal == "STRONG":
            alignment = "✅ HOLD — signal supports position"
        elif signal == "NEUTRAL":
            alignment = "⚠️ HOLD — monitor closely"
        elif signal == "WEAK":
            alignment = "🔴 REVIEW — consider trimming"
        elif signal == "CRITICAL":
            alignment = "🚨 EXIT — signal says remove"
        else:
            alignment = "❓ NOT IN UNIVERSE — review thesis fit"

        portfolio.append({
            "ticker"       : ticker,
            "shares"       : round(shares, 4),
            "avg_cost"     : round(avg_cost, 2),
            "current_price": round(current_price, 2),
            "market_value" : round(market_value, 2),
            "gain_loss_pct": round(gain_loss_pct, 1),
            "weight"       : round(weight, 1),
            "score"        : round(score, 1) if score else None,
            "signal"       : signal,
            "action"       : action,
            "alignment"    : alignment,
        })

    # Sort by market value descending
    portfolio.sort(key=lambda x: x["market_value"], reverse=True)

    return {
        "positions"   : portfolio,
        "total_value" : round(total_value, 2),
        "position_count": len(portfolio),
    }


def identify_gaps(positions, scores):
    """
    Identify STRONG signal names not currently held.
    These are bench players ready to come on the field.
    
    Returns:
        list of tickers with STRONG signal not in portfolio
    """
    held_tickers = {p.get("ticker") for p in positions}

    gaps = []
    for s in scores:
        if s["signal"] == "STRONG" and s["ticker"] not in held_tickers:
            gaps.append({
                "ticker" : s["ticker"],
                "score"  : s["composite"],
                "action" : "Consider adding — STRONG signal, not currently held",
            })

    return sorted(gaps, key=lambda x: x["score"], reverse=True)


def generate_portfolio_report(portfolio_view, gaps, cash):
    """
    Generate markdown portfolio report.
    """
    today = date.today().strftime("%B %d, %Y")
    lines = []

    lines.append("# Hypersonic Defense Screener — Portfolio Report")
    lines.append(f"## Agentic Account (••••5038) — {today}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| | |")
    lines.append(f"|---|---|")
    lines.append(f"| Positions | {portfolio_view['position_count']} |")
    lines.append(f"| Invested | ${portfolio_view['total_value']:,.2f} |")
    lines.append(f"| Cash | ${cash:,.2f} |")
    lines.append(f"| Total | ${portfolio_view['total_value'] + cash:,.2f} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Positions
    lines.append("## Current Positions (On the Field)")
    lines.append("")

    if portfolio_view["positions"]:
        lines.append("| Ticker | Shares | Avg Cost | Price | Value | G/L% | Weight | Score | Signal | Alignment |")
        lines.append("|--------|-------:|---------:|------:|------:|-----:|-------:|------:|--------|-----------|")

        for p in portfolio_view["positions"]:
            score_str = f"{p['score']:.1f}" if p['score'] else "N/A"
            gl_str    = f"+{p['gain_loss_pct']}%" if p['gain_loss_pct'] >= 0 else f"{p['gain_loss_pct']}%"
            lines.append(
                f"| {p['ticker']} "
                f"| {p['shares']} "
                f"| ${p['avg_cost']} "
                f"| ${p['current_price']} "
                f"| ${p['market_value']:,.2f} "
                f"| {gl_str} "
                f"| {p['weight']}% "
                f"| {score_str} "
                f"| {p['signal']} "
                f"| {p['alignment']} |"
            )
    else:
        lines.append("> No positions currently held in Agentic account.")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Gaps — bench players ready to come on
    lines.append("## Bench Players Ready to Come On")
    lines.append("")
    lines.append("*STRONG signal names not currently held*")
    lines.append("")

    if gaps:
        lines.append("| Ticker | Score | Action |")
        lines.append("|--------|------:|--------|")
        for g in gaps:
            lines.append(
                f"| {g['ticker']} "
                f"| {g['score']:.1f} "
                f"| {g['action']} |"
            )
    else:
        lines.append("> All STRONG signal names are currently held.")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated by Hypersonic Defense Screener — {today}*")

    return "\n".join(lines)


def save_portfolio_report(markdown):
    """Save portfolio report to logs folder."""
    today    = date.today().strftime("%Y-%m-%d")
    filename = f"portfolio_{today}.md"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root  = os.path.dirname(script_dir)
    logs_dir   = os.path.join(repo_root, "logs")
    filepath   = os.path.join(logs_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"Portfolio report saved: logs/{filename}")
    return filepath


def run_portfolio(positions=None, cash=0):
    """
    Run portfolio analysis.
    
    Args:
        positions : list of position dicts (from Robinhood)
        cash      : available cash in account
    """
    if positions is None:
        positions = []

    print("Running portfolio analysis...")

    scores         = score_universe()
    portfolio_view = build_portfolio_view(positions, scores)
    gaps           = identify_gaps(positions, scores)
    markdown       = generate_portfolio_report(portfolio_view, gaps, cash)

    save_portfolio_report(markdown)
    print(markdown)

    return portfolio_view, gaps


if __name__ == "__main__":
    # Test with empty portfolio
    run_portfolio(positions=[], cash=1000)