# rebalance.py
# Second Layer Capital — Rebalancing Engine
# Hybrid Score-Informed, Weight-Bound rebalancing system
#
# Rules:
# - Shock triggers: >13.5% or <6.5% → immediate risk review
# - Drift trigger: >2% from target for 30 days → queue for rebalance
# - 10% cash reserve mandatory — never deployed
# - Tier weights: Disruptor 15%, Standard 10%, Anchor 5%
# - Score optimization: ±2% boundary around tier target
# - Output: report + Y/N confirmation before execution

import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from universe import UNIVERSE
from score import score_universe
from positions import POSITIONS, CASH, LAST_UPDATED

# --- Tier Classification ---

TIERS = {
    # Disruptors — 15% raw target
    "PLTR": "Disruptor",
    "AVAV": "Disruptor",
    "KTOS": "Disruptor",
    "KRMN": "Disruptor",
    "AXON": "Disruptor",

    # Standards — 10% raw target
    "HWM" : "Standard",
    "ATI" : "Standard",
    "TDY" : "Standard",
    "HEI" : "Standard",
    "LOAR": "Standard",
    "CW"  : "Standard",
    "MTRN": "Standard",  # Reclassified from Anchor — Q2 2026 earnings

    # Anchors — 5% raw target (none currently)
}

TIER_WEIGHTS = {
    "Disruptor": 15,
    "Standard" : 10,
    "Anchor"   : 5,
}

# --- Configuration ---
CASH_RESERVE_PCT    = 0.10   # 10% mandatory cash reserve
SHOCK_HIGH          = 0.135  # 13.5% shock trigger
SHOCK_LOW           = 0.065  # 6.5% shock trigger
DRIFT_THRESHOLD     = 0.020  # 2% drift threshold
SCORE_BOUNDARY      = 0.020  # ±2% score optimization boundary


def get_current_prices():
    """
    Get current prices for all held positions via yfinance.
    Returns dict of {ticker: price}
    """
    import yfinance as yf
    prices = {}
    for ticker in POSITIONS.keys():
        try:
            data = yf.download(ticker, period="1d", 
                             progress=False, interval="1d")
            if not data.empty:
                prices[ticker] = round(data["Close"].iloc[-1].item(), 2)
        except Exception:
            pass
    return prices


def calculate_portfolio_value(prices):
    """
    Calculate total portfolio value including cash.
    """
    invested = sum(
        POSITIONS[ticker]["shares"] * prices.get(ticker, 0)
        for ticker in POSITIONS
    )
    return round(invested + CASH, 2)


def calculate_deployed_capital(total_value):
    """
    Calculate deployable capital after cash reserve.
    """
    reserve  = round(total_value * CASH_RESERVE_PCT, 2)
    deployed = round(total_value - reserve, 2)
    return deployed, reserve


def normalize_weights(scores):
    """
    Normalize tier weights to sum to 100% of deployed capital.
    Applies ±2% score optimization within tier boundary.
    
    Returns dict of {ticker: target_pct}
    """
    # Calculate raw weights for held + universe tickers
    raw_weights = {}
    score_lookup = {s["ticker"]: s["composite"] for s in scores}

    for ticker in UNIVERSE.keys():
        tier = TIERS.get(ticker, "Standard")
        base = TIER_WEIGHTS[tier]

        # Apply score optimization ±2%
        score = score_lookup.get(ticker, 60)
        if score >= 75:
            adjustment = SCORE_BOUNDARY        # Top of boundary
        elif score >= 50:
            adjustment = 0                      # Mid boundary
        else:
            adjustment = -SCORE_BOUNDARY       # Bottom of boundary

        raw_weights[ticker] = base + (adjustment * 100)

    # Normalize to sum to 100
    total_raw = sum(raw_weights.values())
    normalized = {
        ticker: round((w / total_raw) * 100, 2)
        for ticker, w in raw_weights.items()
    }

    return normalized


def identify_triggers(positions_with_value, total_value, target_weights):
    """
    Identify shock triggers and drift conditions.
    
    Returns:
        shock_triggers: list of immediate action items
        drift_items: list of drift conditions
    """
    shock_triggers = []
    drift_items    = []

    for ticker, data in positions_with_value.items():
        current_pct = data["current_pct"]
        target_pct  = target_weights.get(ticker, 0) / 100

        deviation = current_pct - target_pct

        # Shock triggers — immediate
        if current_pct > SHOCK_HIGH:
            shock_triggers.append({
                "ticker"     : ticker,
                "type"       : "SHOCK HIGH",
                "current_pct": round(current_pct * 100, 1),
                "target_pct" : round(target_pct * 100, 1),
                "deviation"  : round(deviation * 100, 1),
                "action"     : "IMMEDIATE — trim to target",
            })
        elif current_pct < SHOCK_LOW and current_pct > 0:
            shock_triggers.append({
                "ticker"     : ticker,
                "type"       : "SHOCK LOW",
                "current_pct": round(current_pct * 100, 1),
                "target_pct" : round(target_pct * 100, 1),
                "deviation"  : round(deviation * 100, 1),
                "action"     : "IMMEDIATE — add to target or review removal",
            })

        # Drift conditions
        elif abs(deviation) > DRIFT_THRESHOLD:
            drift_items.append({
                "ticker"     : ticker,
                "current_pct": round(current_pct * 100, 1),
                "target_pct" : round(target_pct * 100, 1),
                "deviation"  : round(deviation * 100, 1),
                "action"     : "TRIM" if deviation > 0 else "ADD",
            })

    return shock_triggers, drift_items


def calculate_trades(positions_with_value, target_weights, 
                     deployed_capital, prices):
    """
    Calculate exact shares and dollar amounts to buy/sell
    to reach target weights.
    
    Returns list of trade dicts.
    """
    trades = []

    for ticker in UNIVERSE.keys():
        target_pct    = target_weights.get(ticker, 0) / 100
        target_value  = deployed_capital * target_pct
        current_value = positions_with_value.get(
            ticker, {}).get("market_value", 0)
        price         = prices.get(ticker, 0)

        if price == 0:
            continue

        delta_value  = target_value - current_value
        delta_shares = delta_value / price

        if abs(delta_value) < 1.00:  # Skip trivial trades
            continue

        trades.append({
            "ticker"       : ticker,
            "action"       : "BUY" if delta_value > 0 else "SELL",
            "delta_shares" : round(abs(delta_shares), 4),
            "delta_value"  : round(abs(delta_value), 2),
            "current_value": round(current_value, 2),
            "target_value" : round(target_value, 2),
            "price"        : price,
        })

    # Sort — sells first, then buys
    trades.sort(key=lambda x: (0 if x["action"] == "SELL" else 1,
                               -x["delta_value"]))
    return trades


def generate_rebalance_report(portfolio_value, deployed_capital,
                               cash_reserve, target_weights,
                               positions_with_value, shock_triggers,
                               drift_items, trades, scores):
    """
    Generate professional rebalance report in markdown.
    """
    today = date.today().strftime("%B %d, %Y")
    score_lookup = {s["ticker"]: s for s in scores}
    lines = []

    lines.append("# Second Layer Capital — Rebalance Report")
    lines.append(f"## {today}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Portfolio summary
    lines.append("## Portfolio Summary")
    lines.append("")
    lines.append(f"| | |")
    lines.append(f"|---|---|")
    lines.append(f"| Total Value | ${portfolio_value:,.2f} |")
    lines.append(f"| Cash Reserve (10%) | ${cash_reserve:,.2f} |")
    lines.append(f"| Deployed Capital | ${deployed_capital:,.2f} |")
    lines.append(f"| Cash Available | ${CASH:,.2f} |")
    lines.append(f"| Positions | {len(POSITIONS)} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Shock triggers
    lines.append("## ⚠️ Shock Triggers (Immediate Action Required)")
    lines.append("")
    if shock_triggers:
        lines.append("| Ticker | Type | Current % | Target % | Deviation | Action |")
        lines.append("|--------|------|----------:|---------:|----------:|--------|")
        for t in shock_triggers:
            lines.append(
                f"| {t['ticker']} | {t['type']} | "
                f"{t['current_pct']}% | {t['target_pct']}% | "
                f"{t['deviation']:+.1f}% | {t['action']} |"
            )
    else:
        lines.append("> ✅ No shock triggers. All positions within bounds.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Drift conditions
    lines.append("## 📊 Drift Conditions (Queue for Scheduled Rebalance)")
    lines.append("")
    if drift_items:
        lines.append("| Ticker | Current % | Target % | Deviation | Action |")
        lines.append("|--------|----------:|---------:|----------:|--------|")
        for d in drift_items:
            lines.append(
                f"| {d['ticker']} | {d['current_pct']}% | "
                f"{d['target_pct']}% | {d['deviation']:+.1f}% | "
                f"{d['action']} |"
            )
    else:
        lines.append("> ✅ No drift conditions detected.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Current positions
    lines.append("## 📈 Current Positions")
    lines.append("")
    lines.append("| Ticker | Shares | Avg Cost | Market Value | Weight | Score | Signal | Tier |")
    lines.append("|--------|-------:|---------:|-------------:|-------:|------:|--------|------|")

    for ticker, data in sorted(positions_with_value.items(),
                               key=lambda x: -x[1]["market_value"]):
        s = score_lookup.get(ticker, {})
        tier = TIERS.get(ticker, "Standard")
        lines.append(
            f"| {ticker} "
            f"| {data['shares']:.4f} "
            f"| ${data['avg_cost']:.2f} "
            f"| ${data['market_value']:,.2f} "
            f"| {data['current_pct']*100:.1f}% "
            f"| {s.get('composite', 'N/A')} "
            f"| {s.get('signal', 'N/A')} "
            f"| {tier} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")

    # Trade orders
    lines.append("## 🔄 Rebalance Trade Orders")
    lines.append("")
    lines.append("> **CONFIRMATION REQUIRED** — Review carefully before executing.")
    lines.append("")

    if trades:
        lines.append("| Action | Ticker | Shares | Est. Value | Current | Target |")
        lines.append("|--------|--------|-------:|-----------:|--------:|-------:|")
        for t in trades:
            lines.append(
                f"| **{t['action']}** "
                f"| {t['ticker']} "
                f"| {t['delta_shares']} "
                f"| ${t['delta_value']:,.2f} "
                f"| ${t['current_value']:,.2f} "
                f"| ${t['target_value']:,.2f} |"
            )

        total_buys  = sum(t["delta_value"] for t in trades 
                         if t["action"] == "BUY")
        total_sells = sum(t["delta_value"] for t in trades 
                         if t["action"] == "SELL")

        lines.append("")
        lines.append(f"**Total sells:** ${total_sells:,.2f} | "
                    f"**Total buys:** ${total_buys:,.2f} | "
                    f"**Net:** ${total_sells - total_buys:+,.2f}")
    else:
        lines.append("> ✅ Portfolio is within target weights. No trades needed.")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated by Second Layer Capital Rebalancing Engine — {today}*")
    lines.append("")
    lines.append("> **Disclaimer:** This report requires manual confirmation "
                "before execution. Nothing here constitutes financial advice.")

    return "\n".join(lines)


def save_report(markdown):
    """Save rebalance report to logs folder."""
    today    = date.today().strftime("%Y-%m-%d")
    filename = f"rebalance_{today}.md"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root  = os.path.dirname(script_dir)
    logs_dir   = os.path.join(repo_root, "logs")
    filepath   = os.path.join(logs_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"Report saved: logs/{filename}")
    return filepath


def run_rebalance(execute=False):
    """
    Run full rebalancing analysis.
    
    Args:
        execute: if True, prompt for confirmation and execute trades
    """
    print("=" * 55)
    print("Second Layer Capital — Rebalancing Engine")
    print(f"Date: {date.today().strftime('%B %d, %Y')}")
    print("=" * 55)
    print()

    # Get current prices
    print("Fetching current prices...")
    prices = get_current_prices()

    if not prices:
        print("ERROR: Could not fetch prices. Aborting.")
        return

    # Portfolio value
    portfolio_value              = calculate_portfolio_value(prices)
    deployed_capital, cash_reserve = calculate_deployed_capital(
        portfolio_value)

    print(f"Portfolio value: ${portfolio_value:,.2f}")
    print(f"Deployed capital: ${deployed_capital:,.2f}")
    print(f"Cash reserve: ${cash_reserve:,.2f}")
    print()

    # Get scores
    print("Running screener...")
    scores = score_universe()

    # Calculate target weights
    target_weights = normalize_weights(scores)

    # Build positions with current values
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

    # Identify triggers
    shock_triggers, drift_items = identify_triggers(
        positions_with_value, portfolio_value, target_weights)

    # Calculate trades
    trades = calculate_trades(
        positions_with_value, target_weights, 
        deployed_capital, prices)

    # Generate report
    report = generate_rebalance_report(
        portfolio_value, deployed_capital, cash_reserve,
        target_weights, positions_with_value,
        shock_triggers, drift_items, trades, scores)

    save_report(report)
    print()
    print(report)

    # Execution
    if execute and trades:
        print("\n" + "=" * 55)
        print("TRADE EXECUTION")
        print("=" * 55)
        print("\nReview the trades above carefully.")
        confirm = input("\nExecute these trades? (Y/N): ").strip().upper()

        if confirm == "Y":
            print("\nExecution confirmed. Passing to Robinhood...")
            # Placeholder — execution via Robinhood MCP in dashboard
            print("NOTE: Execute trades manually via Claude + Robinhood MCP")
        else:
            print("\nExecution cancelled. No trades placed.")

    return trades, shock_triggers


if __name__ == "__main__":
    run_rebalance(execute=False)