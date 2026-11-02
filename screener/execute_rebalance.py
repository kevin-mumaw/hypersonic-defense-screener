# execute_rebalance.py
# Automated Rebalancing Execution — Phase 3 Module 3
# Generates rebalance trade orders and executes via Robinhood MCP
# REQUIRES manual Y/N confirmation before any trade is placed
# Shock triggers execute immediately — drift trades queue for 30 days

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from positions import (POSITIONS, CASH, LAST_UPDATED, OVERRIDES,
                       WATCH, MIN_BUY_SCORE)
from rebalance import (
    get_current_prices,
    calculate_portfolio_value,
    calculate_deployed_capital,
    normalize_weights,
    identify_triggers,
    calculate_trades,
    generate_rebalance_report,
    save_report,
    SHOCK_HIGH,
    SHOCK_LOW,
)
from score import score_universe
from drift_history import get_consecutive_drift_days, record_daily_weights


def build_positions_with_value(prices, portfolio_value):
    """Build positions dict with current market values."""
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
    return positions_with_value


MIN_TRADE = 5.00   # smallest buy worth placing


def active_override(ticker):
    """Return (reason, expiry) if a manual override is active today, else None."""
    override = OVERRIDES.get(ticker)
    if override:
        reason, expiry = override
        if date.today() <= date.fromisoformat(expiry):
            return reason, expiry
    return None


def filter_executable_trades(trades, shock_triggers, drift_items,
                             cash, reserve, scores=None):
    """
    Split trades into executable now vs deferred, and fund the buys.

    Rules:
    - Active override (positions.py OVERRIDES): deferred, no trade
    - Shock trigger: candidate for immediate execution
    - Drift 30+ calendar days: candidate for execution
    - Drift under 30 days: deferred
    - Within 2% of target: no trade (deferred)
    - Buys may only use sale proceeds plus cash above the 10% reserve.
      If candidate buys exceed that, every buy is scaled down pro rata.
    - All trades still require manual confirmation.

    Returns:
        executable, deferred, funding (dict with the cash math)
    """
    shock_tickers = {t["ticker"] for t in shock_triggers}
    drift_tickers = {d["ticker"] for d in drift_items}

    score_lookup = {s["ticker"]: s["composite"] for s in (scores or [])}
    candidates = []
    deferred   = []

    for trade in trades:
        ticker = trade["ticker"]
        days   = get_consecutive_drift_days(ticker)
        ov     = active_override(ticker)

        if trade["action"] == "BUY" and ticker in WATCH:
            trade["reason"] = f"BUY BLOCKED — WATCH: {WATCH[ticker]}"
            deferred.append(trade)
        elif (trade["action"] == "BUY" and ticker in shock_tickers
              and scores is not None
              and score_lookup.get(ticker, 0) < MIN_BUY_SCORE):
            trade["reason"] = (f"BUY BLOCKED — score "
                               f"{score_lookup.get(ticker, 0)} < {MIN_BUY_SCORE}")
            deferred.append(trade)
        elif ov:
            trade["reason"] = f"OVERRIDE ACTIVE until {ov[1]} — no trade"
            deferred.append(trade)
        elif ticker in shock_tickers:
            trade["reason"] = "SHOCK TRIGGER — immediate execution"
            candidates.append(trade)
        elif ticker in drift_tickers and days >= 30:
            trade["reason"] = f"DRIFT {days} DAYS — qualified for rebalance"
            candidates.append(trade)
        elif ticker in drift_tickers:
            trade["reason"] = f"DRIFT {days}/30 DAYS — deferred, monitoring"
            deferred.append(trade)
        else:
            trade["reason"] = "WITHIN 2% OF TARGET — no trade"
            deferred.append(trade)

    sells = [t for t in candidates if t["action"] == "SELL"]
    buys  = [t for t in candidates if t["action"] == "BUY"]

    sell_total = sum(t["delta_value"] for t in sells)
    buy_wanted = sum(t["delta_value"] for t in buys)
    spare_cash = max(0.0, cash - reserve)

    # Sells exist to fund approved buys. Size them to the buys, not to target.
    sells_needed = max(0.0, buy_wanted - spare_cash)
    sell_scale   = 1.0
    if sell_total > sells_needed:
        sell_scale = sells_needed / sell_total if sell_total > 0 else 0.0
    sold = []
    for t in sells:
        value = round(t["delta_value"] * sell_scale, 2)
        if value < MIN_TRADE:
            t["reason"] += " — NOT NEEDED (no approved buy to fund)"
            deferred.append(t)
            continue
        if sell_scale < 1.0:
            t["reason"] += f" — sized to {sell_scale*100:.0f}% to fund approved buys only"
        t["delta_value"]  = value
        t["delta_shares"] = round(value / t["price"], 4)
        sold.append(t)
    sells = sold
    sell_total_used = sum(t["delta_value"] for t in sells)

    buy_budget = sell_total_used + spare_cash
    scale      = 1.0
    if buy_wanted > buy_budget:
        scale = buy_budget / buy_wanted if buy_wanted > 0 else 0.0

    funded_buys = []
    for t in buys:
        value = round(t["delta_value"] * scale, 2)
        if value < MIN_TRADE:
            t["reason"] += " — UNFUNDED (insufficient cash above reserve)"
            deferred.append(t)
            continue
        if scale < 1.0:
            t["reason"] += f" — scaled to {scale*100:.0f}% (cash reserve protected)"
        t["delta_value"]  = value
        t["delta_shares"] = round(value / t["price"], 4)
        funded_buys.append(t)

    buy_total = sum(t["delta_value"] for t in funded_buys)
    funding = {
        "sell_total"   : round(sell_total_used, 2),
        "buy_wanted"   : round(buy_wanted, 2),
        "buy_total"    : round(buy_total, 2),
        "spare_cash"   : round(spare_cash, 2),
        "cash_after"   : round(cash + sell_total_used - buy_total, 2),
        "reserve"      : round(reserve, 2),
        "scale"        : scale,
    }

    return sells + funded_buys, deferred, funding


def display_execution_plan(executable, deferred, portfolio_value,
                           cash, funding):
    """Display the execution plan for review."""
    print("\n" + "=" * 60)
    print("REBALANCE EXECUTION PLAN")
    print(f"Date: {date.today().strftime('%B %d, %Y')}")
    print(f"Portfolio Value: ${portfolio_value:,.2f}")
    print(f"Cash on hand: ${cash:,.2f} | Reserve (10%): ${funding['reserve']:,.2f}")
    print("=" * 60)

    if executable:
        print(f"\n✅ EXECUTABLE NOW ({len(executable)} trades):")
        print("-" * 60)
        for t in executable:
            print(f"  {t['action']:<4} {t['ticker']:<6} "
                  f"${t['delta_value']:>8.2f} "
                  f"({t['delta_shares']} shares @ ${t['price']:.2f})")
            print(f"       {t['reason']}")

        print(f"\n  Total SELL: ${funding['sell_total']:,.2f}")
        print(f"  Total BUY:  ${funding['buy_total']:,.2f} "
              f"(wanted ${funding['buy_wanted']:,.2f})")
        print(f"  Cash after trades: ${funding['cash_after']:,.2f} "
              f"(reserve ${funding['reserve']:,.2f})")
        if funding["cash_after"] + 0.01 < min(cash, funding["reserve"]):
            print("  ⚠️  Trades would push cash below the reserve.")
        elif funding["cash_after"] + 0.01 < funding["reserve"]:
            print("  ℹ️  Cash was already below the reserve before these "
                  "trades; they do not reduce it.")
    else:
        print("\n✅ No trades executable right now.")

    if deferred:
        print(f"\n⏳ NOT EXECUTING ({len(deferred)} trades):")
        print("-" * 60)
        for t in deferred:
            print(f"  {t['action']:<4} {t['ticker']:<6} "
                  f"${t['delta_value']:>8.2f} — {t['reason']}")

    print("\n" + "=" * 60)


def confirm_and_execute(executable, account_number="644565038"):
    """
    Request manual confirmation and execute approved trades.
    
    NOTE: Actual execution requires Robinhood MCP connection
    via Claude conversation. This function generates the 
    execution payload for use in the Claude interface.
    """
    if not executable:
        print("No trades to execute.")
        return []

    print("\n⚠️  CONFIRMATION REQUIRED")
    print("Review the trades above carefully.")
    print("These trades will be placed in Agentic account ••••5038")
    print()

    confirm = input("Execute these trades? (Y/N): ").strip().upper()

    if confirm != "Y":
        print("\nExecution cancelled. No trades placed.")
        return []

    print("\n✅ Confirmed. Generating execution payload...")
    print()
    print("Copy the following and execute via Claude + Robinhood MCP:")
    print("-" * 60)

    for trade in executable:
        action = "buy" if trade["action"] == "BUY" else "sell"
        print(f"Place {action} order: ${trade['delta_value']:.2f} "
              f"of {trade['ticker']} at market")

    print("-" * 60)
    print()
    print("After execution, update screener/positions.py with new positions.")

    return executable


def run_execute_rebalance(auto_confirm=False):
    """
    Run the full rebalancing execution workflow.

    Args:
        auto_confirm: if True skip confirmation prompt (for testing only)
    """
    print("=" * 60)
    print("Second Layer Capital — Rebalancing Execution Engine")
    print(f"Date: {date.today().strftime('%B %d, %Y')}")
    print("=" * 60)
    print()

    # Get current data
    print("Fetching current prices...")
    prices          = get_current_prices()
    missing = [t for t in POSITIONS if not prices.get(t)]
    if missing:
        print(f"ERROR: no price for {', '.join(missing)}. "
              f"Aborting — nothing calculated, nothing saved.")
        return []
    portfolio_value = calculate_portfolio_value(prices)
    deployed, reserve = calculate_deployed_capital(portfolio_value)

    print(f"Portfolio: ${portfolio_value:,.2f} | "
          f"Deployed: ${deployed:,.2f} | "
          f"Reserve: ${reserve:,.2f}")
    print()

    # Run screener
    print("Running screener...")
    scores         = score_universe()
    target_weights = normalize_weights(scores)

    # Build positions
    positions_with_value = build_positions_with_value(
        prices, portfolio_value)

    # Record drift history
    record_daily_weights(positions_with_value, target_weights)

    # Identify triggers
    shock_triggers, drift_items = identify_triggers(
        positions_with_value, portfolio_value, target_weights)

    # Calculate all trades
    all_trades = calculate_trades(
        positions_with_value, target_weights,
        deployed, prices)

    # Filter to executable vs deferred
    executable, deferred, funding = filter_executable_trades(
        all_trades, shock_triggers, drift_items, CASH, reserve, scores)

    # Generate and save full report
    report = generate_rebalance_report(
        portfolio_value, deployed, reserve,
        target_weights, positions_with_value,
        shock_triggers, drift_items, all_trades, scores)
    save_report(report)

    # Display execution plan
    display_execution_plan(
        executable, deferred, portfolio_value, CASH, funding)

    # Confirm and execute
    if auto_confirm:
        executed = executable
    else:
        executed = confirm_and_execute(executable)

    return executed


if __name__ == "__main__":
    run_execute_rebalance()