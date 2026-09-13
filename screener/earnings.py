# earnings.py
# Earnings Calendar Integration — Phase 3 Module 4
# Fetches upcoming earnings dates for held positions
# Flags earnings within 7 days in daily briefing
# Warns when a gap alert coincides with upcoming earnings

import yfinance as yf
import os
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from positions import POSITIONS
from universe import UNIVERSE


def get_earnings_dates(tickers):
    """
    Fetch upcoming earnings dates for a list of tickers.
    
    Returns:
        dict of {ticker: earnings_date or None}
    """
    earnings = {}

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            cal   = stock.calendar

            if cal is not None and not cal.empty:
                # Get earnings date
                if "Earnings Date" in cal.index:
                    earn_date = cal.loc["Earnings Date"].iloc[0]
                    if hasattr(earn_date, 'date'):
                        earn_date = earn_date.date()
                    earnings[ticker] = earn_date
                else:
                    earnings[ticker] = None
            else:
                earnings[ticker] = None

        except Exception as e:
            earnings[ticker] = None

    return earnings


def check_earnings_alerts(earnings_dates, gap_flags=None, days_warning=7):
    """
    Check for upcoming earnings and flag alerts.

    Args:
        earnings_dates : dict of {ticker: date}
        gap_flags      : dict of {ticker: gap_flag_string} from signals
        days_warning   : number of days ahead to warn

    Returns:
        list of alert dicts
    """
    alerts     = []
    today      = date.today()
    cutoff     = today + timedelta(days=days_warning)
    gap_flags  = gap_flags or {}

    for ticker, earn_date in earnings_dates.items():
        if earn_date is None:
            continue

        days_until = (earn_date - today).days

        if 0 <= days_until <= days_warning:
            alert = {
                "ticker"    : ticker,
                "earn_date" : earn_date.strftime("%B %d, %Y"),
                "days_until": days_until,
                "has_gap"   : ticker in gap_flags and gap_flags[ticker] is not None,
                "gap_flag"  : gap_flags.get(ticker),
            }
            alerts.append(alert)

    # Sort by days until earnings
    alerts.sort(key=lambda x: x["days_until"])
    return alerts


def generate_earnings_report(earnings_dates, alerts):
    """
    Generate markdown earnings section for daily briefing.
    """
    today = date.today().strftime("%B %d, %Y")
    lines = []

    lines.append("## 📅 Earnings Calendar")
    lines.append("")

    if alerts:
        lines.append("### ⚠️ Earnings Within 7 Days")
        lines.append("")
        for a in alerts:
            days_str = "TODAY" if a["days_until"] == 0 else \
                      "TOMORROW" if a["days_until"] == 1 else \
                      f"in {a['days_until']} days"

            line = f"- **{a['ticker']}** — earnings {days_str} ({a['earn_date']})"

            if a["has_gap"]:
                line += f" ⚠️ GAP ALERT: {a['gap_flag']}"

            lines.append(line)
            lines.append(f"  > Review position size before earnings. "
                        f"Consider reducing if outsized gain/loss risk.")

        lines.append("")

    # Full calendar for held positions
    lines.append("### 📋 Upcoming Earnings — All Held Positions")
    lines.append("")

    held_earnings = {k: v for k, v in earnings_dates.items()
                    if k in POSITIONS and v is not None}

    if held_earnings:
        lines.append("| Ticker | Earnings Date | Days Until |")
        lines.append("|--------|--------------|----------:|")

        for ticker, earn_date in sorted(held_earnings.items(),
                                        key=lambda x: x[1]):
            days_until = (earn_date - date.today()).days
            if days_until >= 0:
                lines.append(
                    f"| {ticker} "
                    f"| {earn_date.strftime('%B %d, %Y')} "
                    f"| {days_until} |"
                )
    else:
        lines.append("> No upcoming earnings dates available.")

    return "\n".join(lines)


def run_earnings_check(gap_flags=None):
    """
    Run full earnings check for all held positions.
    """
    print("Checking earnings calendar for held positions...")

    tickers       = list(POSITIONS.keys())
    earnings      = get_earnings_dates(tickers)
    alerts        = check_earnings_alerts(earnings, gap_flags=gap_flags)
    report        = generate_earnings_report(earnings, alerts)

    print(report)
    return earnings, alerts


if __name__ == "__main__":
    run_earnings_check()