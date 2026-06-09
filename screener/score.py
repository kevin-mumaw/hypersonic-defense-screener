# score.py
# Calculates composite scores for all tickers in the universe
# Scoring weights per SCREENER_SPEC.md:
#   Technical:   40%
#   Fundamental: 40% (Phase 2 — real data from fundamentals.py)
#   Thesis:      20% (Phase 1 placeholder — manual input)
# Scores range 0-100
# Thresholds: 75-100 Strong, 50-74 Neutral, 25-49 Weak, 0-24 Critical

from signals import calculate_universe_signals
from fundamentals import fetch_universe_fundamentals, score_fundamentals


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
    Phase 2: Uses real fundamental data from fundamentals.py
    Falls back to neutral 50 if data unavailable.
    """
    if fund_data is None:
        return 50  # Neutral fallback

    result = score_fundamentals(fund_data)
    return result["fundamental_score"]


def score_thesis(ticker):
    """
    Score the thesis component 0-100.
    Phase 1: Manual placeholder — all tickers start neutral.
    Phase 2: Will incorporate contract wins, program milestones,
             defense revenue mix, removal trigger flags.

    To override for a specific ticker, add it to THESIS_OVERRIDES.
    """
    THESIS_OVERRIDES = {
        "KRMN": 85,  # Purpose-built hypersonics, $500M+ pipeline
        "KTOS": 80,  # Hypersonic test platforms, directly on-thesis
        "AVAV": 75,  # Switchblade, autonomous systems — solid thesis fit
        "TDY" : 75,  # Defense electronics, harsh environment subsystems
        "HWM" : 70,  # Advanced materials, refractory alloys
        "ATI" : 70,  # Titanium alloys, hypersonic airframes
        "LOAR": 65,  # Components business, less hypersonics-specific
        "HEI" : 65,  # Defense electronics, more MRO than hypersonics
        "MTRN": 65,  # Materials relevant, thin margins reduce conviction
        "SXI" : 45,  # Partial thesis fit — too diversified
        "VELO": 40,  # High risk, pre-profitability, extreme volatility
        "PLTR": 85,  # Unique DoD AI command layer — no public proxy. Premium valuation caps score
        "AXON": 75,  # IoMT/drone software moat. Defense secondary to law enforcement today
    }

    return THESIS_OVERRIDES.get(ticker, 60)  # Default neutral-positive


def calculate_composite_score(ticker, signals, fund_data=None):
    """
    Calculate weighted composite score for a single ticker.

    Returns:
        dict with component scores and composite
    """
    tech_score   = score_technical(signals)
    fund_score   = score_fundamental(ticker, fund_data)
    thesis_score = score_thesis(ticker)

    composite = (
        tech_score   * 0.40 +
        fund_score   * 0.40 +
        thesis_score * 0.20
    )

    # Signal interpretation
    if composite >= 75:
        signal = "STRONG"
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
        "thesis"      : round(thesis_score, 1),
        "composite"   : round(composite, 1),
        "signal"      : signal,
        "action"      : action,
    }


def score_universe():
    """
    Score all tickers in the universe and return ranked results.
    """
    all_signals      = calculate_universe_signals(period="6mo")
    all_fundamentals = fetch_universe_fundamentals()

    scores = []
    for ticker, signals in all_signals.items():
        fund_data = all_fundamentals.get(ticker, None)
        score     = calculate_composite_score(ticker, signals, fund_data)
        scores.append(score)

    # Rank by composite score descending
    scores.sort(key=lambda x: x["composite"], reverse=True)

    print("\n--- Composite Scores ---\n")
    print(f"{'Rank':<5} {'Ticker':<6} {'Tech':>6} "
          f"{'Fund':>6} {'Thesis':>7} "
          f"{'Score':>7} {'Signal':<10} Action")
    print("-" * 70)

    for i, s in enumerate(scores, 1):
        print(
            f"{i:<5} "
            f"{s['ticker']:<6} "
            f"{s['technical']:>6.1f} "
            f"{s['fundamental']:>6.1f} "
            f"{s['thesis']:>7.1f} "
            f"{s['composite']:>7.1f} "
            f"{s['signal']:<10} "
            f"{s['action']}"
        )

    return scores


if __name__ == "__main__":
    scores = score_universe()