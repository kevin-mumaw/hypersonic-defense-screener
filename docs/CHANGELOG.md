# Hypersonic Defense Screener — Changelog

This document records all significant decisions, changes, 
and rationale throughout the development of the 
Hypersonic Defense Screener. It is maintained as a 
living document updated with every meaningful change 
to thesis, universe, screener logic, or methodology.

---

## [0.4] — June 2026

### Screener — Initial Build Complete
- Added universe.py — single source of truth for ticker universe
- Added data.py — yfinance price data pull for full universe
- Added signals.py — technical signal calculation (MA20, MA50, 
  MA200, RSI, volume confirmation, trend)
- Added score.py — composite scoring with technical, fundamental, 
  and thesis components
- Added report.py — narrative daily briefing with universe posture 
  and grouped signal observations
- Phase 1 screener operational — 11/11 tickers pulling clean data

## [0.3] — June 2026

### Screener (SCREENER_SPEC.md)
- Created initial screener specification v0.1
- Defined design principles, signal framework, 
  scoring methodology, output format, position 
  sizing guidelines, technology stack, and 
  phased development plan
- Weights set at 40% technical, 40% fundamental, 
  20% thesis — subject to adjustment as system develops
- Noted honest limitations including yfinance data 
  quality, survivorship bias, and small universe size

## [0.2] — June 2026

### Universe (UNIVERSE.md)
- Added ATI Inc (ATI) — specialty titanium and nickel 
  superalloys critical for hypersonic airframes and 
  thermal protection systems
- Added Heico Corporation (HEI) — defense electronic 
  technologies and aerospace components
- Added Standex International (SXI) — partial thesis 
  fit; multi-industry manufacturer with aerospace/defense 
  segment. Flagged for monitoring due to diversification
- Added Teledyne Technologies (TDY) — defense electronics, 
  harsh environment subsystems, optical components
- Removed formal tier assignments — deferred until 
  screener development provides clearer signal data 
  and fundamental comparison
- Added removal trigger: federal investigation into 
  foreign adversary control, infiltration, or ownership. 
  Rationale: national security risk and contract 
  vulnerability are disqualifying independent of 
  legal outcome given sensitivity of hypersonics 
  supply chain

---

## [0.1] — June 2026

### Project Initialized
- Created private GitHub repository: 
  hypersonic-defense-screener
- Established folder structure: thesis, universe, 
  screener, backtest, docs, logs
- Added .gitignore (Python), LICENSE.md (proprietary), 
  README.md (thesis summary)

### Thesis (THESIS.md)
- Drafted initial investment thesis v0.1
- Core thesis: picks-and-shovels play on the 
  hypersonics and next-generation defense supply chain
- Defined technology domains in scope: propulsion, 
  thermal protection, advanced materials, guidance 
  and navigation, directed energy components, 
  autonomous systems hardware, ground and test 
  infrastructure
- Defined out of scope: prime contractors, pure 
  software, international defense companies, 
  commercial aerospace without defense exposure
- Thesis horizon: 5 to 10 years minimum
- Edge statement corrected: author has general 
  defense industry familiarity, not specialized 
  or non-public knowledge. All research conducted 
  using publicly available information only.

### Universe (UNIVERSE.md v0.1)
- Established inclusion criteria: US-listed, 
  meaningful defense/hypersonics exposure, 
  picks-and-shovels layer, sufficient liquidity, 
  US-headquartered
- Initial universe: KRMN, HWM, MTRN, KTOS, 
  LOAR, AVAV, VELO
- Initial watchlist: BWX, MRCY, AIRO
- Noted portfolio overlap with existing space 
  infrastructure holdings: HWM, MTRN, KTOS
- Flagged key risks: KRMN pullback from highs, 
  VELO volatility, SXI diversification

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| June 2026 | Chose hypersonics/next-gen defense as primary thesis | Author has defense industry familiarity; thesis has multi-decade structural tailwind; picks-and-shovels layer under-covered by retail |
| June 2026 | Excluded prime contractors from universe | Too well-covered, fairly valued, not picks-and-shovels |
| June 2026 | Deferred tier assignments | Premature without screener signal data to validate relative ranking |
| June 2026 | Added foreign adversary removal trigger | Supply chain security is core to thesis; infiltration risk is disqualifying regardless of legal outcome |
| June 2026 | Corrected edge statement in thesis | Accuracy and honesty required — especially if this becomes a public Autopilot Pilot |

---

*This changelog follows semantic versioning loosely 
adapted for a research and investment project:*
- *Major versions (1.0, 2.0) — fundamental thesis changes*
- *Minor versions (0.1, 0.2) — universe or methodology changes*
- *Patch versions (0.1.1) — corrections and clarifications*
