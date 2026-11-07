# thesis.py
# Single source of truth for manual thesis score overrides (0-100).
# Imported by score.py (drives the composite) and intelligence.py
# (drives the alert text). The two used to keep separate hardcoded
# copies that already disagreed — CW was 80 in score.py and "N/A" in
# intelligence.py, VELO was 60 by default vs 40, and SXI sat at 45 in
# both although it left the universe in July 2026. Those dead entries
# are deleted here (2026-11-07, see docs/CHANGELOG.md [2.10]).
#
# Every universe ticker must have an explicit entry: get_thesis_score()
# raises instead of silently defaulting to 60, so a new ticker added
# to the universe without an override fails loudly rather than
# scoring an unearned "neutral-positive" 60.
# Record thesis changes in docs/CHANGELOG.md with date and reason.

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
    "PLTR": 85,  # Unique DoD AI command layer — no public proxy. Premium valuation caps score
    "AXON": 75,  # IoMT/drone software moat. Defense secondary to law enforcement today
    "CW"  : 80,  # Defense electronics, naval nuclear, picks-and-shovels fit
}


def get_thesis_score(ticker):
    """
    Return the explicit thesis override for a ticker.

    Raises ValueError if the ticker has no entry — every universe
    ticker must have one. A silent 60 default hid missing overrides.
    """
    if ticker not in THESIS_OVERRIDES:
        raise ValueError(
            f"No thesis score override for {ticker} — add one to "
            f"screener/thesis.py (see docs/CHANGELOG.md [2.10])")
    return THESIS_OVERRIDES[ticker]
