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
# - Output: filtered report + execution payload (manual via Robinhood MCP)
#
# 2026-11-07 fix (audit findings 1-14): the report's trade table is now
# generated from execute_rebalance.filter_executable_trades — the one
# authoritative path. The unfiltered calculate_trades output is no
# longer printed as orders; deferred trades are listed with reasons.
# Prices are fetched for all 12 universe tickers; a missing price for a
# held ticker aborts the run instead of valuing the holding at $0.

import copy
import os
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from universe import UNIVERSE
from score import score_universe
from positions import POSITIONS, CASH, LAST_UPDATED
from drift_history import get_consecutive_drift_days

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
DRIFT_DAYS_REQUIRED = 30     # drift must persist this many days


def _eastern_offset_manual(now_utc):
    """UTC offset for America/New_York by the US daylight-saving rule.

    DST runs from the second Sunday in March 02:00 local (07:00 UTC)
    to the first Sunday in November 02:00 local (06:00 UTC).
    Used only when the zoneinfo database is unavailable (e.g. Windows
    without the tzdata package).
    """
    year = now_utc.year
    march1 = date(year, 3, 1)
    dst_start_day = march1 + timedelta(days=(6 - march1.weekday()) % 7 + 7)
    nov1 = date(year, 11, 1)
    dst_end_day = nov1 + timedelta(days=(6 - nov1.weekday()) % 7)
    dst_start_utc = datetime(year, 3, dst_start_day.day, 7,
                             tzinfo=timezone.utc)
    dst_end_utc = datetime(year, 11, dst_end_day.day, 6,
                           tzinfo=timezone.utc)
    if dst_start_utc <= now_utc < dst_end_utc:
        return timedelta(hours=-4)
    return timedelta(hours=-5)


def eastern_now():
    """Current datetime in America/New_York.

    Uses zoneinfo when the tz database is available; falls back to the
    manual US DST rule so the report is dated in ET even on machines
    without tzdata. Returns an aware datetime when zoneinfo works,
    otherwise a naive datetime holding ET wall time.
    """
    now_utc = datetime.now(timezone.utc)
    try:
        return now_utc.astimezone(ZoneInfo("America/New_York"))
    except Exception:
        return (now_utc + _eastern_offset_manual(now_utc)).replace(
            tzinfo=None)


def get_current_prices():
    """
    Get current prices for all universe tickers plus any held tickers
    outside the universe, via yfinance.
    Returns dict of {ticker: price}
    """
    import yfinance as yf
    prices = {}
    tickers = list(UNIVERSE.keys())
    for ticker in POSITIONS.keys():
        if ticker not in tickers:
            tickers.append(ticker)
    for ticker in tickers:
        try:
            data = yf.download(ticker, period="1d",
                             progress=False, interval="1d")
            if not data.empty:
                prices[ticker] = round(data["Close"].iloc[-1].item(), 2)
        except Exception:
            pass
    return prices


def missing_held_prices(prices):
    """Held tickers with no price in the fetched dict."""
    return [t for t in POSITIONS if not prices.get(t)]


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

    # Renormalize after rounding so the weights sum to exactly 100.00
    # (per-ticker rounding can otherwise land at 99.99 or 100.01).
    # The residual goes on the largest weight, where it matters least.
    diff = round(100.00 - sum(normalized.values()), 2)
    if diff:
        largest = max(normalized, key=lambda t: normalized[t])
        normalized[largest] = round(normalized[largest] + diff, 2)

    return normalized


def identify_triggers(positions_with_value, total_value, target_weights):
    """
    Identify shock triggers and drift conditions.
    Respects manual overrides in positions.py OVERRIDES dict.
    Drift items carry the logged consecutive drift days so the
    30-day rule is visible in the report.

    Returns:
        shock_triggers: list of immediate action items
        drift_items: list of drift conditions
    """
    from positions import OVERRIDES
    from datetime import date

    shock_triggers = []
    drift_items    = []

    for ticker, data in positions_with_value.items():
        # No price data — nothing here can be evaluated. The run aborts
        # on a missing held price (see run_rebalance); this guard keeps
        # a zeroed price from inventing a trigger when the function is
        # called directly (a zeroed ticker used to land in drift as
        # "ADD" while the trade table silently skipped it).
        if data.get("price", 0) == 0:
            continue

        current_pct = data["current_pct"]
        target_pct  = target_weights.get(ticker, 0) / 100
        deviation   = current_pct - target_pct

        # Check for manual override
        override = OVERRIDES.get(ticker)
        if override:
            reason, expiry = override
            if date.today() <= date.fromisoformat(expiry):
                # Still within override window — skip shock trigger
                drift_items.append({
                    "ticker"     : ticker,
                    "current_pct": round(current_pct * 100, 1),
                    "target_pct" : round(target_pct * 100, 1),
                    "deviation"  : round(deviation * 100, 1),
                    "action"     : f"OVERRIDE ACTIVE until {expiry} — {reason[:60]}...",
                })
                continue

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
                "days"       : get_consecutive_drift_days(ticker),
                "action"     : "TRIM" if deviation > 0 else "ADD",
            })

    return shock_triggers, drift_items


def calculate_trades(positions_with_value, target_weights,
                     deployed_capital, prices):
    """
    Calculate exact shares and dollar amounts to buy/sell
    to reach target weights.

    Returns list of trade dicts. This is the RAW target-minus-current
    list — the input to execute_rebalance.filter_executable_trades,
    not an order list. It must not be printed as orders.
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

    # Off-universe holdings: sell to zero explicitly — never silently
    # drop a flagged position from the trade table. (A held ticker
    # with no price is skipped here; the run aborts on a missing held
    # price, so a completed run always has one.)
    for ticker, pos in positions_with_value.items():
        if ticker in UNIVERSE:
            continue
        price = prices.get(ticker, 0)
        if price == 0:
            continue
        current_value = pos.get("market_value", 0)
        if abs(current_value) < 1.00:  # Skip trivial trades
            continue
        trades.append({
            "ticker"       : ticker,
            "action"       : "SELL",
            "delta_shares" : round(pos["shares"], 4),
            "delta_value"  : round(abs(current_value), 2),
            "current_value": round(current_value, 2),
            "target_value" : 0.0,
            "price"        : price,
            "off_universe" : True,
        })

    # Sort — sells first, then buys
    trades.sort(key=lambda x: (0 if x["action"] == "SELL" else 1,
                               -x["delta_value"]))
    return trades


def generate_rebalance_report(portfolio_value, deployed_capital,
                               cash_reserve, target_weights,
                               positions_with_value, shock_triggers,
                               drift_items, trades, scores,
                               executable=None, deferred=None,
                               funding=None, missing_prices=None):
    """
    Generate professional rebalance report in markdown.

    The trade table shows ONLY the trades that passed
    execute_rebalance.filter_executable_trades (overrides, WATCH,
    score gate, 30-day drift rule, funding). Deferred trades are
    listed with their reasons. If executable/deferred/funding are
    not supplied, they are computed here from `trades` (used by
    execute_rebalance.py, which calls this with the raw trade list).
    """
    today = eastern_now()
    today_str = today.strftime("%B %d, %Y")
    score_lookup = {s["ticker"]: s for s in scores}
    lines = []

    # --- One authoritative path: filter the raw trades. ---
    # (Lazy import — execute_rebalance imports this module, so a
    # top-level import would be circular.)
    if executable is None or deferred is None or funding is None:
        from execute_rebalance import filter_executable_trades
        trades_copy = [dict(t) for t in trades]
        for t in trades_copy:
            t.pop("reason", None)  # filter rebuilds reasons from scratch
        executable, deferred, funding = filter_executable_trades(
            trades_copy, shock_triggers, drift_items, CASH, cash_reserve,
            scores)

    lines.append("# Second Layer Capital — Rebalance Report")
    lines.append(f"## {today_str} (America/New_York)")
    lines.append("")
    lines.append("> **Filtered report** — the trades below passed the "
                "override, WATCH, score-gate, 30-day drift, and funding "
                "filters (`execute_rebalance.filter_executable_trades`). "
                "Deferred trades are listed with their reasons. This is "
                "the one authoritative trade list; the raw "
                "target-minus-current table is not shown as orders.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Score completeness warning
    missing_scores = [t for t in UNIVERSE if t not in score_lookup]
    if missing_scores:
        lines.append("## ⚠️ SCORE DATA INCOMPLETE — TARGETS PROVISIONAL")
        lines.append("")
        lines.append(f"> No score fetched for: "
                    f"{', '.join(missing_scores)}. Targets for missing "
                    f"tickers default to 60 (no score adjustment) and are "
                    f"provisional — re-run when the screener returns all "
                    f"12 scores.")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Portfolio summary + reserve position
    invested = sum(d["market_value"]
                   for d in positions_with_value.values())
    reserve_shortfall = round(max(0.0, cash_reserve - CASH), 2)
    lines.append("## Portfolio Summary")
    lines.append("")
    lines.append(f"| | |")
    lines.append(f"|---|---|")
    lines.append(f"| Total Value | ${portfolio_value:,.2f} |")
    lines.append(f"| Cash Reserve (10%) | ${cash_reserve:,.2f} |")
    lines.append(f"| Deployed Capital | ${deployed_capital:,.2f} |")
    lines.append(f"| Cash Available | ${CASH:,.2f} |")
    lines.append(f"| Reserve Shortfall | ${reserve_shortfall:,.2f} |")
    lines.append(f"| Positions | {len(POSITIONS)} |")
    lines.append("")
    if reserve_shortfall > 0:
        lines.append(f"> Cash is ${reserve_shortfall:,.2f} below the 10% "
                    f"reserve. Restoring it requires that much net "
                    f"selling — see Funding below.")
    else:
        lines.append("> Cash meets the 10% reserve.")
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
    lines.append("## 📊 Drift Conditions (30-day rule — qualified at 30+ days)")
    lines.append("")
    if drift_items:
        lines.append("| Ticker | Current % | Target % | Deviation | Days | Action |")
        lines.append("|--------|----------:|---------:|----------:|-----:|--------|")
        for d in drift_items:
            days = d.get("days")
            if days is None:
                days_str = "—"
                action = d["action"]
            elif days >= DRIFT_DAYS_REQUIRED:
                days_str = str(days)
                action = (f"{d['action']} — DRIFT {days} DAYS "
                          f"(qualified)")
            else:
                days_str = f"{days}/{DRIFT_DAYS_REQUIRED}"
                action = (f"{d['action']} — DRIFT {days}/"
                          f"{DRIFT_DAYS_REQUIRED} DAYS (monitoring)")
            lines.append(
                f"| {d['ticker']} | {d['current_pct']}% | "
                f"{d['target_pct']}% | {d['deviation']:+.1f}% | "
                f"{days_str} | {action} |"
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

    # Trade orders — filtered only
    lines.append("## 🔄 Rebalance Trade Orders (Filtered)")
    lines.append("")
    lines.append("> **CONFIRMATION REQUIRED** — Review carefully before "
                "executing. Only the trades below passed all filters.")
    lines.append("")

    def _reason(t):
        reason = t.get("reason", "")
        if t.get("off_universe"):
            reason += (" — OFF-UNIVERSE holding (target $0 — sell to "
                       "zero when reviewed)")
        return reason

    if executable:
        lines.append(f"### ✅ Executable Now ({len(executable)} trades)")
        lines.append("")
        lines.append("| Action | Ticker | Shares | Est. Value | Current | Target | Reason |")
        lines.append("|--------|--------|-------:|-----------:|--------:|-------:|--------|")
        for t in executable:
            lines.append(
                f"| **{t['action']}** "
                f"| {t['ticker']} "
                f"| {t['delta_shares']} "
                f"| ${t['delta_value']:,.2f} "
                f"| ${t['current_value']:,.2f} "
                f"| ${t['target_value']:,.2f} "
                f"| {_reason(t)} |"
            )
        lines.append("")
        lines.append(f"**Total sells:** ${funding['sell_total']:,.2f} | "
                    f"**Total buys:** ${funding['buy_total']:,.2f} "
                    f"(wanted ${funding['buy_wanted']:,.2f}) | "
                    f"**Net:** "
                    f"${funding['sell_total'] - funding['buy_total']:+,.2f}")
    else:
        lines.append("> ✅ No trades executable right now.")
    lines.append("")

    if deferred:
        lines.append(f"### ⏳ Deferred — Not Executing ({len(deferred)} trades)")
        lines.append("")
        lines.append("| Action | Ticker | Est. Value | Reason |")
        lines.append("|--------|--------|-----------:|--------|")
        for t in deferred:
            lines.append(
                f"| **{t['action']}** "
                f"| {t['ticker']} "
                f"| ${t['delta_value']:,.2f} "
                f"| {_reason(t)} |"
            )
        lines.append("")

    # Funding line — buys depend on the sells executing first
    executable_net = round(funding["sell_total"] - funding["buy_total"], 2)
    remaining_shortfall = round(
        max(0.0, reserve_shortfall - executable_net), 2)
    lines.append(f"**Funding:** buys ${funding['buy_total']:,.2f} (wanted "
                f"${funding['buy_wanted']:,.2f}) are funded by "
                f"${funding['sell_total']:,.2f} of sale proceeds + "
                f"${funding['spare_cash']:,.2f} cash above the 10% reserve "
                f"(${funding['reserve']:,.2f}). Cash after trades: "
                f"${funding['cash_after']:,.2f}. **Buys execute only if "
                f"their funding sells execute first.**")
    lines.append("")
    lines.append(f"Reserve after these trades: shortfall "
                f"${remaining_shortfall:,.2f} "
                f"(executable trades net "
                f"${executable_net:+,.2f}).")
    lines.append("")

    # Unheld tickers with no price — target unreachable, not traded
    if missing_prices:
        lines.append("### ⚠️ No Price — Not Traded")
        lines.append("")
        for t in missing_prices:
            target_value = round(
                deployed_capital * target_weights.get(t, 0) / 100, 2)
            lines.append(f"- **{t}** — target ${target_value:,.2f} "
                        f"unreachable: no price fetched, not traded.")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"*Generated by Second Layer Capital Rebalancing Engine — {today_str} (America/New_York)*")
    lines.append("")
    lines.append("> **Disclaimer:** This report requires manual confirmation "
                "before execution. Nothing here constitutes financial advice.")

    return "\n".join(lines)


def save_report(markdown):
    """Save rebalance report to logs folder."""
    today    = eastern_now().strftime("%Y-%m-%d")
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

    The report's trade table comes from
    execute_rebalance.filter_executable_trades — the one authoritative
    path. A missing price for a held ticker aborts the run before
    anything is calculated or saved.

    Args:
        execute: if True, prompt to print the execution payload for
            the executable trades (nothing is placed by this module)
    """
    print("=" * 55)
    print("Second Layer Capital — Rebalancing Engine")
    print(f"Date: {eastern_now().strftime('%B %d, %Y')} (America/New_York)")
    print("=" * 55)
    print()

    # Get current prices — all 12 universe tickers plus any held
    # tickers outside the universe.
    print("Fetching current prices...")
    prices = get_current_prices()

    # Fail closed on a missing price for a held ticker: a holding
    # valued at $0 corrupts every weight and trigger in the report.
    missing_held = missing_held_prices(prices)
    if missing_held:
        print(f"ERROR: no price for {', '.join(missing_held)}. "
              f"Aborting — nothing calculated, nothing saved.")
        return None

    if not prices:
        print("ERROR: Could not fetch prices. Aborting.")
        return None

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

    missing_scores = [t for t in UNIVERSE
                      if t not in {s["ticker"] for s in scores}]
    if missing_scores:
        print(f"WARNING: no score for {', '.join(missing_scores)} — "
              f"targets provisional (missing tickers default to 60).")

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

    # Calculate trades (raw target-minus-current — the filter's input,
    # never printed as orders)
    trades = calculate_trades(
        positions_with_value, target_weights,
        deployed_capital, prices)

    missing_prices = [t for t in UNIVERSE if t not in prices]

    # One authoritative path: filter the raw trades.
    # (Lazy import — execute_rebalance imports this module, so a
    # top-level import would be circular.)
    from execute_rebalance import filter_executable_trades
    executable, deferred, funding = filter_executable_trades(
        trades, shock_triggers, drift_items, CASH, cash_reserve, scores)

    # Generate report
    report = generate_rebalance_report(
        portfolio_value, deployed_capital, cash_reserve,
        target_weights, positions_with_value,
        shock_triggers, drift_items, trades, scores,
        executable=executable, deferred=deferred, funding=funding,
        missing_prices=missing_prices)

    save_report(report)
    print()
    print(report)

    # Execution payload (manual — nothing is placed by this module)
    if execute and executable:
        print("\n" + "=" * 55)
        print("TRADE EXECUTION PAYLOAD")
        print("=" * 55)
        print("\nReview the trades above carefully.")
        confirm = input(
            "\nPrint the execution payload for these trades? (Y/N): "
        ).strip().upper()

        if confirm == "Y":
            print("\nCopy the following and execute via Claude + Robinhood MCP:")
            print("-" * 60)
            for t in executable:
                action = "buy" if t["action"] == "BUY" else "sell"
                print(f"Place {action} order: ${t['delta_value']:.2f} "
                      f"of {t['ticker']} at market")
            print("-" * 60)
            print("\nNOTE: Nothing was placed by this module. Execute "
                  "trades manually via Claude + Robinhood MCP, then "
                  "update screener/positions.py.")
        else:
            print("\nExecution cancelled. No trades placed.")

    return trades, shock_triggers


if __name__ == "__main__":
    run_rebalance(execute=False)
