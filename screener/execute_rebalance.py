# execute_rebalance.py
# Automated Rebalancing Execution — Phase 3 Module 3
# Generates rebalance trade orders and executes via Robinhood MCP
# REQUIRES manual Y/N confirmation before any trade is placed
# Shock triggers execute immediately — drift trades queue for 30 days

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from positions import POSITIONS, CASH, LAST_UPDATED
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


def filter_executable_trades(trades, shock_triggers, 
                              drift_items, target_weights):
    """
    Filter trades to only those that should execute now.

    Rules:
    - Shock trigger trades: execute immediately
    - Drift trades: only execute if 30+ consecutive days of drift
    - All trades require manual confirmation

    Returns:
        executable: list of trades to execute now
        deferred  : list of trades deferred (drift < 30 days)
    """
    shock_tickers = {t["ticker"] for t in shock_triggers}

    executable = []
    deferred   = []

    for trade in trades:
        ticker     = trade["ticker"]
        consec_days = get_consecutive_drift_days(ticker)

        if ticker in shock_tickers:
            trade["reason"] = f"SHOCK TRIGGER — immediate execution required"
            executable.append(trade)
        elif consec_days >= 30:
            trade["reason"] = f"DRIFT 30+ DAYS — qualified for rebalance ({consec_days} days)"
            executable.append(trade)
        else:
            trade["reason"] = f"DRIFT {consec_days}/30 DAYS — deferred, monitoring"
            deferred.append(trade)

    return executable, deferred


def display_execution_plan(executable, deferred, portfolio_value, cash):
    """Display the execution plan for review."""
    print("\n" + "=" * 60)
    print("REBALANCE EXECUTION PLAN")
    print(f"Date: {date.today().strftime('%B %d, %Y')}")
    print(f"Portfolio Value: ${portfolio_value:,.2f}")
    print(f"Cash Available: ${cash:,.2f}")
    print("=" * 60)

    if executable:
        print(f"\n✅ EXECUTABLE NOW ({len(executable)} trades):")
        print("-" * 60)
        total_sells = sum(t["delta_value"] for t in executable 
                         if t["action"] == "SELL")
        total_buys  = sum(t["delta_value"] for t in executable 
                         if t["action"] == "BUY")

        for t in executable:
            print(f"  {t['action']:<4} {t['ticker']:<6} "
                  f"${t['delta_value']:>8.2f} "
                  f"({t['delta_shares']} shares @ ${t['price']:.2f})")
            print(f"       {t['reason']}")

        print(f"\n  Total SELL: ${total_sells:,.2f}")
        print(f"  Total BUY:  ${total_buys:,.2f}")
        print(f"  Net Cash:   ${total_sells - total_buys:+,.2f}")
    else:
        print("\n✅ No trades executable right now.")
        print("   Either no shock triggers or drift < 30 days on all positions.")

    if deferred:
        print(f"\n⏳ DEFERRED ({len(deferred)} trades — monitoring):")
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
    executable, deferred = filter_executable_trades(
        all_trades, shock_triggers, drift_items, target_weights)

    # Generate and save full report
    report = generate_rebalance_report(
        portfolio_value, deployed, reserve,
        target_weights, positions_with_value,
        shock_triggers, drift_items, all_trades, scores)
    save_report(report)

    # Display execution plan
    display_execution_plan(
        executable, deferred, portfolio_value, CASH)

    # Confirm and execute
    if auto_confirm:
        executed = executable
    else:
        executed = confirm_and_execute(executable)

    return executed


if __name__ == "__main__":
    run_execute_rebalance()