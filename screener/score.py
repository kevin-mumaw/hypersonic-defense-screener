# score.py
# Calculates composite scores for all tickers in the universe
# Scoring weights per SCREENER_SPEC.md:
#   Technical:   40%
#   Fundamental: 40% (Phase 2 — real data from fundamentals.py)
#   Thesis:      20% (manual overrides in thesis.py — single source of truth)
# Scores range 0-100
# Thresholds: 75-100 Strong, 50-74 Neutral, 25-49 Weak, 0-24 Critical
#
# Failure semantics (fixed 2026-11-07, score.py audit findings 1-3, 7):
#   - A ticker that fails to fetch, or whose series is too short to
#     compute the components, is EXCLUDED from the ranking and listed
#     in the missing list returned alongside the scores — a partial
#     run never again prints as a complete ranking.
#   - "No fundamental data" has one answer everywhere: the component
#     falls back to a flat 50 and is marked N/A in the output.
#   - RSI is the simple-moving-average variant (see signals.py).

from signals import calculate_universe_signals
from fundamentals import (fetch_universe_fundamentals,
                          score_fundamentals,
                          get_fundamentals_cache_info)
from thesis import get_thesis_score as score_thesis
from positions import MIN_BUY_SCORE
from universe import UNIVERSE


def score_technical(signals):
    """
    Score the technical component 0-100.
    Based on: trend, RSI, MA relationships, volume confirmation.
    """
    score = 0

    # Trend (40 points)
    if signals["trend"] == "BULLISH":
        score += 40
    elif signals["trend"] == "MIXED":
        score += 20
    # BEARISH = 0

    # RSI (30 points)
    rsi = signals["rsi"]
    if 40 <= rsi <= 60:
        score += 30  # Ideal range
    elif 30 <= rsi < 40 or 60 < rsi <= 70:
        score += 15  # Acceptable range
    elif rsi > 70:
        score += 5   # Overbought — extended, penalize
    elif rsi < 30:
        score += 10  # Oversold — potential reversal

    # MA20 vs MA50 cross (20 points)
    if signals["ma20_vs_ma50"]:
        score += 20  # MA20 above MA50 — bullish

    # Volume confirmation (10 points)
    if signals["vol_confirmed"]:
        score += 10

    return min(score, 100)


def score_fundamental(ticker, fund_data):
    """
    Score the fundamental component 0-100.

    Returns (score, available): available is False when there is no
    fundamental data at all — the score is then the flat-50 fallback
    and the caller must mark the component N/A in the output, not
    print 50 as if it were a measurement.
    """
    if fund_data is None:
        return 50, False

    result = score_fundamentals(fund_data)
    if result is None:
        return 50, False

    return result["fundamental_score"], True


def calculate_composite_score(ticker, signals, fund_data=None):
    """
    Calculate weighted composite score for a single ticker.

    Returns:
        dict with component scores and composite
    """
    tech_score   = score_technical(signals)
    fund_score, fund_available = score_fundamental(ticker, fund_data)
    thesis_score = score_thesis(ticker)

    composite = (
        tech_score   * 0.40 +
        fund_score   * 0.40 +
        thesis_score * 0.20
    )

    # Check for gap flag
    gap_flag = signals.get("gap_flag", None)

    if composite >= 75:
        signal = "STRONG"
        if gap_flag:
            action = f"Consider adding — {gap_flag}"
        else:
            action = "Consider adding"
    elif composite >= 50:
        signal = "NEUTRAL"
        action = "Hold / monitor"
    elif composite >= 25:
        signal = "WEAK"
        action = "Consider trimming"
    else:
        signal = "CRITICAL"
        action = "Review for removal"

    return {
        "ticker"      : ticker,
        "technical"   : round(tech_score, 1),
        "fundamental" : round(fund_score, 1),
        "fundamental_available": fund_available,
        "thesis"      : round(thesis_score, 1),
        "composite"   : round(composite, 1),
        "signal"      : signal,
        "action"      : action,
        # Buy gate (MIN_BUY_SCORE, positions.py): a shock-low buy for a
        # BLOCK ticker is deferred by execute_rebalance's filter.
        # Printed in the ranked table so the label and the gate agree
        # visibly — ATI at 54.4 is NEUTRAL but BLOCK, which the old
        # table never showed.
        "buy_gate"    : ("PASS" if round(composite, 1) >= MIN_BUY_SCORE
                         else "BLOCK"),
    }


def score_universe():
    """
    Score all tickers in the universe and return ranked results.

    Returns (scores, missing, signals):
        scores  — ranked list of score dicts, highest composite first
        missing — [{ticker, reason}] for every universe ticker not
                  scored: price fetch failed, or the series was too
                  short to compute the components
        signals — the technical signals dict (already fetched here),
                  so callers do not fetch the universe a second time
    """
    all_signals      = calculate_universe_signals(period="6mo")
    all_fundamentals = fetch_universe_fundamentals()

    scores = []
    missing = []
    for ticker in UNIVERSE.keys():
        signals = all_signals.get(ticker)
        if signals is None:
            missing.append({"ticker": ticker,
                            "reason": "price fetch failed"})
            continue
        if signals.get("insufficient_data"):
            missing.append({"ticker": ticker,
                            "reason": f"insufficient data "
                                      f"({signals.get('rows', '?')} rows, "
                                      f"need 50)"})
            continue
        fund_data = all_fundamentals.get(ticker, None)
        score     = calculate_composite_score(ticker, signals, fund_data)
        scores.append(score)

    # Rank by composite score descending
    scores.sort(key=lambda x: x["composite"], reverse=True)

    cache_info = get_fundamentals_cache_info()
    total = len(UNIVERSE)

    print("\n--- Composite Scores ---\n")
    if missing:
        names = ", ".join(f"{m['ticker']} ({m['reason']})"
                          for m in missing)
        print(f"⚠️  WARNING: {len(missing)} of {total} tickers missing "
              f"from this ranking: {names}.")
        print("   The ranking below is PARTIAL — do not treat it as complete.")
    else:
        print(f"All {total} universe tickers scored.")
    if cache_info["stale"]:
        print(f"⚠️  WARNING: fundamentals cache is "
              f"{cache_info['age_days']} days old "
              f"(cached: {cache_info['cached_date']}) — older than the "
              f"7-day refresh cadence. Fundamental scores may be stale.")
    print()
    print(f"{'Rank':<5} {'Ticker':<6} {'Tech':>6} "
          f"{'Fund':>6} {'Thesis':>7} "
          f"{'Score':>7} {'Signal':<10} {'Gate':<5} Action")
    print("-" * 76)

    for i, s in enumerate(scores, 1):
        fund_str = ("N/A" if not s["fundamental_available"]
                    else f"{s['fundamental']:.1f}")
        print(
            f"{i:<5} "
            f"{s['ticker']:<6} "
            f"{s['technical']:>6.1f} "
            f"{fund_str:>6} "
            f"{s['thesis']:>7.1f} "
            f"{s['composite']:>7.1f} "
            f"{s['signal']:<10} "
            f"{s['buy_gate']:<5} "
            f"{s['action']}"
        )

    print()
    print(f"Buy gate: composite >= {MIN_BUY_SCORE} (MIN_BUY_SCORE) — a "
          f"shock-low buy for a BLOCK ticker is deferred by the "
          f"rebalance filter.")

    return scores, missing, all_signals


if __name__ == "__main__":
    scores, missing, signals = score_universe()
