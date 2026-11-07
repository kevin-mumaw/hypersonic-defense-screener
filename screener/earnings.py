# earnings.py
# Earnings Calendar Integration — Phase 3 Module 4
# Fetches upcoming earnings dates for held positions
# Flags earnings within 7 days in daily briefing
# Warns when a gap alert coincides with upcoming earnings
#
# 2026-11-07 fix (audit findings 1-7): get_earnings_dates parses both
# the dict calendar shape (yfinance >= 1.x, a list of dates under
# "Earnings Date") and the DataFrame shape (yfinance <= 0.2.x), and
# normalizes every value to a plain date at the fetch boundary.
# Fetch failures are recorded separately from "no date scheduled", and
# the run is dated in America/New_York. The alert window logic itself
# (0-7 days inclusive) was verified correct and is unchanged.

import yfinance as yf
import os
import sys
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from positions import POSITIONS
from universe import UNIVERSE


def _eastern_offset_manual(now_utc):
    """UTC offset for America/New_York by the US daylight-saving rule.

    DST runs from the second Sunday in March 02:00 local (07:00 UTC)
    to the first Sunday in November 02:00 local (06:00 UTC).
    Used only when the zoneinfo database is unavailable (e.g. Windows
    without the tzdata package). Mirrors rebalance.py.
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


def eastern_today():
    """Today's date in America/New_York (Kevin's timezone).

    Uses zoneinfo when the tz database is available; falls back to the
    manual US DST rule so the run is dated in ET even on machines
    without tzdata. Mirrors rebalance.py's eastern_now().
    """
    now_utc = datetime.now(timezone.utc)
    try:
        return now_utc.astimezone(ZoneInfo("America/New_York")).date()
    except Exception:
        return (now_utc + _eastern_offset_manual(now_utc)).replace(
            tzinfo=None).date()


def _to_date(value):
    """Normalize an earnings-date value to a plain date, or None.

    Accepts date, datetime, and pandas Timestamp (a datetime
    subclass). Anything else is not a date — returns None.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _parse_calendar(cal):
    """Parse one ticker's yfinance calendar payload.

    Returns (earn_date or None, failure_reason or None).
    earn_date is None when no date is scheduled — deliberately, not
    via an exception. failure_reason is set only when the payload
    could not be read at all; "no date scheduled" is NOT a failure.
    """
    if cal is None:
        return None, None

    if isinstance(cal, dict):
        values = cal.get("Earnings Date")
        if values is None:
            return None, None
        # The dict value is a list (sometimes a range of two dates);
        # element [0] is the date Yahoo knows. A scalar is accepted
        # defensively but is not a shape yfinance currently returns.
        if isinstance(values, (list, tuple)):
            if not values:
                return None, None
            parsed = _to_date(values[0])
            if parsed is None:
                return None, "unreadable earnings date value"
            return parsed, None
        parsed = _to_date(values)
        if parsed is None:
            return None, "unreadable earnings date value"
        return parsed, None

    # DataFrame shape (yfinance <= 0.2.x) — duck-typed so this module
    # does not need a pandas import. Kept as the original path.
    if hasattr(cal, "empty") and hasattr(cal, "loc"):
        try:
            if cal.empty:
                return None, None
            if "Earnings Date" in cal.index:
                parsed = _to_date(cal.loc["Earnings Date"].iloc[0])
                if parsed is None:
                    return None, "unreadable earnings date value"
                return parsed, None
            return None, None
        except Exception:
            return None, "unreadable calendar data"

    return None, "unreadable calendar data"


def fetch_earnings_calendar(tickers):
    """
    Fetch earnings dates for a list of tickers.

    Returns:
        (earnings, failures)
        earnings: dict of {ticker: earnings_date or None} — None means
            no date is scheduled for that ticker.
        failures: dict of {ticker: reason} — the calendar could not be
            fetched or read for these tickers. A failure is NOT the
            same as "no date scheduled".
    """
    earnings = {}
    failures = {}

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            cal = stock.calendar
        except Exception as e:
            failures[ticker] = (
                f"fetch failed ({type(e).__name__}: {e})")
            earnings[ticker] = None
            continue

        earn_date, reason = _parse_calendar(cal)
        earnings[ticker] = earn_date
        if reason is not None:
            failures[ticker] = reason

    return earnings, failures


def get_earnings_dates(tickers):
    """
    Fetch upcoming earnings dates for a list of tickers.

    Returns:
        dict of {ticker: earnings_date or None}
    Kept for callers that only need dates; use
    fetch_earnings_calendar when failures matter.
    """
    earnings, _failures = fetch_earnings_calendar(tickers)
    return earnings


def check_earnings_alerts(earnings_dates, gap_flags=None, days_warning=7,
                          today=None):
    """
    Check for upcoming earnings and flag alerts.

    Args:
        earnings_dates : dict of {ticker: date}
        gap_flags      : dict of {ticker: gap_flag_string} from signals
        days_warning   : number of days ahead to warn
        today          : date to anchor the window on (defaults to
                         today in America/New_York)

    Returns:
        list of alert dicts
    """
    alerts = []
    today = today or eastern_today()
    cutoff = today + timedelta(days=days_warning)
    gap_flags = gap_flags or {}

    for ticker, earn_date in earnings_dates.items():
        if earn_date is None:
            continue

        days_until = (earn_date - today).days

        if 0 <= days_until <= days_warning:
            alert = {
                "ticker": ticker,
                "earn_date": earn_date.strftime("%B %d, %Y"),
                "days_until": days_until,
                "has_gap": ticker in gap_flags and gap_flags[ticker] is not None,
                "gap_flag": gap_flags.get(ticker),
            }
            alerts.append(alert)

    # Sort by days until earnings
    alerts.sort(key=lambda x: x["days_until"])
    return alerts


def generate_earnings_report(earnings_dates, alerts, failures=None,
                             today=None):
    """
    Generate markdown earnings section for daily briefing.

    failures: dict of {ticker: reason} from fetch_earnings_calendar —
        tickers whose calendar could not be fetched or read. They are
        reported as unavailable data, never as "no earnings scheduled".
    today: date to anchor the table on (defaults to today in
        America/New_York).
    """
    failures = failures or {}
    today = today or eastern_today()
    today_str = today.strftime("%B %d, %Y")
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
            days_until = (earn_date - today).days
            if days_until >= 0:
                lines.append(
                    f"| {ticker} "
                    f"| {earn_date.strftime('%B %d, %Y')} "
                    f"| {days_until} |"
                )

        if failures:
            failed = ", ".join(sorted(failures))
            lines.append("")
            lines.append(
                f"> ⚠️ Earnings data unavailable for {len(failures)} "
                f"ticker(s): {failed} — fetch failed, not "
                f"\"no earnings scheduled\"."
            )
    elif failures:
        if len(failures) >= len(earnings_dates) and earnings_dates:
            lines.append(
                "> ⚠️⚠️ Earnings calendar unavailable for ALL held "
                "positions — the fetch failed for every ticker. Do not "
                "read this as \"no upcoming earnings\"."
            )
        else:
            failed = ", ".join(sorted(failures))
            lines.append(
                f"> ⚠️ Earnings data unavailable for {len(failures)} "
                f"ticker(s): {failed}."
            )
    else:
        lines.append("> No upcoming earnings dates available.")

    return "\n".join(lines)


def run_earnings_check(gap_flags=None, today=None):
    """
    Run the full earnings check for all held positions.

    Returns (earnings, alerts, failures). Prints nothing except a
    progress line — the caller decides what to print; see
    generate_earnings_report for the markdown section.
    """
    print("Checking earnings calendar for held positions...")

    tickers = list(POSITIONS.keys())
    earnings, failures = fetch_earnings_calendar(tickers)
    alerts = check_earnings_alerts(earnings, gap_flags=gap_flags,
                                   today=today)
    return earnings, alerts, failures


if __name__ == "__main__":
    _earnings, _alerts, _failures = run_earnings_check()
    print(generate_earnings_report(_earnings, _alerts, _failures))
