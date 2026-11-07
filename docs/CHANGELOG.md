# Hypersonic Defense Screener — Changelog

This document records all significant decisions, changes, 
and rationale throughout the development of the 
Hypersonic Defense Screener. It is maintained as a 
living document updated with every meaningful change 
to thesis, universe, screener logic, or methodology.
---

## [2.9] — November 2026

### Earnings Calendar — Dict Parse, Failure Distinction, ET Dating
- `get_earnings_dates` parses both yfinance calendar shapes: the
  dict (yfinance >= 1.x, "Earnings Date" list, element [0]) and the
  DataFrame (yfinance <= 0.2.x, original path kept). Every value is
  normalized to a plain `date` at the fetch boundary.
- The module had never returned a date: with yfinance 1.8.0 the
  dict has no `.empty`, so every ticker raised AttributeError and
  the bare except recorded None. The briefing printed "No upcoming
  earnings dates available" while the data was there. On 2026-11-04
  a working parser would have alerted on five held names (AXON, CW,
  LOAR, KRMN, KTOS); AXON reported 11-05 and gapped -18.2% on 11-06.
- Fetch failures are now recorded separately from "no date
  scheduled" (`fetch_earnings_calendar` returns (earnings,
  failures)); the report warns "earnings data unavailable for N
  tickers" and louder when ALL tickers fail, instead of printing
  "no upcoming earnings" as a fact.
- report.py's bare `except: pass` around the earnings section is
  replaced with a visible "Earnings data unavailable (reason)"
  placeholder — the section can no longer vanish silently.
- Alert window and report are dated in America/New_York
  (`eastern_today()`, mirroring rebalance.py's `eastern_now()`),
  so `days_until` matches Kevin's calendar. `run_earnings_check`
  no longer prints the section itself (it printed twice in a full
  briefing run); it returns (earnings, alerts, failures) and the
  caller prints.
- requirements.txt: the `yfinance==0.2.51` pin is dropped
  (intentionally unpinned). The pin is what let this break
  silently — the workflows already install latest unpinned, and
  the module now accepts both calendar shapes.
- Fixes from the 2026-11-06/07 earnings.py audit (27 synthetic +
  live cases, all passing; live runs verified: HEI 2026-12-17 and
  PLTR 2027-02-01 in the table, no alerts within 7 days, section
  prints once in the briefing).

## [2.10] — November 2026

### Scoring — Partial Runs Visible, One Missing-Data Answer, Thesis Dedup
- `score_universe()` now returns (scores, missing, signals): a ticker
  that fails to fetch, or whose series is too short to compute the
  components (< 50 rows for MA50), is excluded from the ranking and
  listed in the missing list with its reason — and the ranked table
  header prints a WARNING naming the missing tickers instead of
  presenting a partial ranking as complete. Before this fix a run
  that fetched 11/12 (PLTR missing, 2026-11-07) printed a ranked
  table numbered 1–11 with no warning. The briefing still runs on a
  partial fetch; it says so.
- `data.py` treats an empty yfinance result as a retryable failure
  (same backoff as an exception), returning None only after 3
  attempts. The old code returned None on the first empty result,
  so the retry never fired for the failure mode that actually
  happens. Live verification: the 2026-11-07 run that dropped PLTR
  before the fix fetched all 12 after it.
- "No fundamental data" now has one answer everywhere:
  `score_fundamentals` returns None when all five scored fields are
  None, and `score.py`'s flat-50 fallback applies uniformly — and
  the component prints N/A in the ranked table and the briefing
  instead of 50 as if it were a measurement. The old code gave 49
  for empty fields vs 50 for a fetch failure, and the 1 point
  flipped the NEUTRAL/WEAK band.
- Thesis scores are a single source of truth: new `screener/thesis.py`
  holds THESIS_OVERRIDES, imported by both score.py and
  intelligence.py (2026-11-07 — the two copies disagreed: CW 80 vs
  "N/A", VELO 60 vs 40, SXI 45 in both though it left the universe
  in July 2026). SXI and VELO are deleted. Every universe ticker
  must have an explicit entry — `get_thesis_score` raises instead
  of silently defaulting to 60. All 12 universe tickers already had
  explicit entries, so no score changed. Record thesis changes here
  with date and reason.
- Fundamentals cache: `fetch_universe_fundamentals` warns loudly
  when the cache is older than the 7-day refresh cadence (and the
  ranked table header says so), via `get_fundamentals_cache_info()`.
  `cache_fundamentals.py` now fetches live (`use_cache=False`) —
  the old code called the cache-first fetch, so a local "refresh"
  re-saved stale data with a fresh date (reproduced 2026-11-07:
  a 2020-dated cache with a poisoned value re-stamped itself
  current). The unused cached "score" field is no longer written;
  score.py never read it. The committed cache file itself was not
  regenerated or modified by this change.
- MA200 and the unimplemented Relative Strength row are removed
  from SCREENER-SPEC.md §4 so the spec matches the code (trend is
  price vs MA20/MA50). The MA200 computation is removed from
  signals.py — nothing consumed it, and it could never compute on
  the 6-month window (~128 rows < 200). The fetch window was NOT
  extended to make MA200 compute: that would change live technical
  scores and is Kevin's call.
- RSI: NOT switched to Wilder's smoothing — that changes live
  scores and is Kevin's call. The SMA variant is now documented
  where the RSI is displayed (signals table, briefing, spec §4.1):
  audit numbers are simple 15.2 vs Wilder's 30.6 on the same
  synthetic closes, a 2.0-composite-point difference. The RSI
  function and the technical-score bands are deduped out of
  backtest.py (it now imports `calculate_rsi` from signals.py and
  `score_technical` from score.py); verified identical outputs on
  a seeded synthetic series.
- Short data: a ticker with < 50 rows is excluded from the ranking
  with an "insufficient data" note and counted as missing — not
  silently scored technical 0.
- Buy gate: MIN_BUY_SCORE stays at 55 (moving it to 50 or 75 would
  change which buys are gated — Kevin's call). The ranked table now
  prints the gate result (PASS/BLOCK) per ticker, so the label and
  the gate agree visibly — ATI at 54.4 is NEUTRAL but BLOCK.
  `filter_executable_trades` now raises if scores is None instead
  of treating None as "no gate". `get_universe_posture` counts WEAK
  and CRITICAL separately (the bearish thresholds still count them
  together; the split is printed in the briefing). `run_report` no
  longer fetches the universe twice — it reuses the signals
  `score_universe` already fetched.
- Fixes from the 2026-11-07 score.py audit (122 synthetic + live
  cases, all passing). Live verification: all 12 composites
  UNCHANGED after the fix — HEI 83.0, KRMN 81.8, TDY 79.8,
  PLTR 69.0, CW 68.8, LOAR 63.0, HWM 60.8, AVAV 60.2, KTOS 58.4,
  AXON 57.8, ATI 54.4, MTRN 48.6.
- Judgment calls left for Kevin (flagged, not decided here):
  (1) the per-field half-credit ladder is unchanged for genuinely
  partial data — AVAV and KRMN each carry 7 unearned points today
  from a None earnings_growth, and "we know nothing" still scores
  49 while "we know it's terrible" scores 0; (2) Wilder's RSI vs
  the SMA variant (above); (3) MIN_BUY_SCORE 55 sits inside the
  NEUTRAL band (50–74); (4) MA200 — extend the fetch window or
  leave the trend as MA20/MA50.

## [2.8] — November 2026

### Rebalancing Engine — One Authoritative (Filtered) Path
- Rebalance report trade table now generated from
  execute_rebalance.filter_executable_trades — the one authoritative
  path. Executable trades are printed as orders; deferred trades are
  listed with their reasons. The unfiltered target-minus-current table
  is no longer printed as orders.
- Fixes from the 2026-11-06/07 rebalance.py audit (125 synthetic cases,
  all passing; live run verified):
  - Trade table no longer sells positions under active overrides
    (PLTR/HWM) or buys WATCH-listed tickers (KRMN) or sub-55-score
    shock-low buys (ATI)
  - Prices fetched for all 12 universe tickers (was held tickers only);
    a missing price for a held ticker aborts the run instead of valuing
    the holding at $0 (verified live: a failed PLTR fetch aborted the
    run cleanly instead of corrupting the report)
  - Funding line printed: buys vs cash on hand plus sale proceeds,
    stating buys depend on the sells executing
  - 30-day drift gate applied in the report (days shown per drift item)
  - Off-universe holdings get an explicit SELL-to-zero trade, never a
    silent omission
  - Reserve position printed: cash vs 10% reserve, shortfall, and the
    cash-raise share of net selling
  - Score input guarded: partial score sets warn and are labelled
    provisional
  - Report dated in America/New_York; weights renormalized to sum to
    exactly 100.00; execute prompt reworded to what actually happens
    (prints a payload — nothing is placed by this module)
- Note: the 30-day drift gate cannot qualify a drift trade until drift
  logging resumes — data/drift_history.json last entry 2026-10-04
  (stale). The gate is implemented; its input is not yet live.
- execute_rebalance.py filter/funding math unchanged (verified
  synthetically in the audit); rebalance.py now imports and uses it.
  Live run on the survey's numbers: no trades executable, all 12
  deferred with reasons — matching the filtered path exactly.

## [2.7] — September 2026

### Rebalancing Engine — Override System
- Added OVERRIDES dict to positions.py
- Rebalancing engine now respects deliberate position decisions
- HWM flagged as DELIBERATE_OVERWEIGHT — contrarian thesis buy
  at discount after SpaceX turbine blade noise
- Override active until November 1 2026 — reassess then
- Shock triggers bypass for overridden positions
- Position shows in Drift Conditions with override notice instead
- Tools no longer "moot" — engine distinguishes accidental drift
  from deliberate thesis decisions

### Portfolio Tracker Fix
- Fixed portfolio.py — now fetches live prices for all positions
- Fixed test data that was showing $0 prices and empty portfolio
- Portfolio report now shows real P&L per position
  
## [2.6] — September 2026

### Phase 3 — Module 3 Complete
- Added execute_rebalance.py — automated rebalancing execution
- 30-day drift buffer enforced — shock triggers execute immediately,
  drift trades only execute after 30 consecutive days
- Manual Y/N confirmation required before any trade placed
- Generates execution payload for Robinhood MCP via Claude
- First run September 12 2026:
  - 6 shock trigger trades identified (HWM, AXON shock high,
    KRMN, KTOS, CW, ATI shock low)
  - NOT executed — deliberate contrarian HWM position,
    selloff is seasonal not thesis-driven
  - HEI and LOAR deferred at day 2/30

## [2.5] — September 2026

### Phase 3 — Module 5 Complete
- Added social.py — social media post generator
- Generates X posts (280 char limit enforced) and LinkedIn posts
- Post types: weekly performance, new position, milestone, thesis validation
- Negative returns include context: "broad market selloff — thesis intact"
- All posts require manual review before publishing
- @SecondLayerCap on X ready for first posts

## [2.4] — September 2026

### Phase 3 — Modules 3 and 4 Complete
- Module 4: earnings.py — earnings calendar integration
  - Flags earnings within 7 days for held positions
  - Warns when gap alert coincides with upcoming earnings
  - Added to daily briefing report automatically
- CW thesis review — HOLD decision
  - Q2 revenue $924M +5%, margin 19.4% +110bps, FCF +37%
  - Down 25% from entry due to broad selloff, NOT company issues
  - Analyst targets $700-857, sole-source naval nuclear intact
- LOAR thesis review — HOLD decision
  - Technical signals historically unreliable — never trade on signals alone
  - Defense revenue +70% YoY, 40%+ EBITDA margins, guidance raised
  - Hold for thesis reasons only

## [2.3] — September 2026

### Phase 3 — Modules 1 and 2 Complete
- Module 1: signal_history.py — daily score tracking, 30-day trend analysis
- Module 2: drift_history.py — 30-day drift buffer now enforced in code
  - Shock triggers fire immediately (13.5%/6.5%)
  - Drift conditions only queue after 30 consecutive days
  - Recent drift shown for monitoring only
- Fixed yfinance MultiIndex NaN price bug — added dropna() to signals.py
- Both modules wired into GitHub Action at midnight ET

### Current Drift Status (September 11 2026)
- HWM SHOCK HIGH 31.5% — intentional contrarian position, hold
- AXON SHOCK HIGH 16.7% — day 1 of tracking
- KRMN SHOCK LOW 3.8% — market selloff, governance watch
- KTOS SHOCK LOW 4.5% — market selloff

## [2.2] — September 2026

### Phase 3 Progress
- Added signal_history.py — daily score tracking, 30-day trend analysis
- Wired signal history into GitHub Action — runs daily at midnight ET
- Fixed yfinance MultiIndex NaN price bug in signals.py
- Changed GitHub Action from 9am to midnight ET — eliminates merge conflicts
- Removed Phase 2 references from daily briefing

### Portfolio Updates
- HWM — added $80 @ $229.52 on September 11 2026
- HWM blended avg cost now $244.82 on 1.184 shares
- PLTR — no change, monitoring
- Cash: $0

### Research
- KRMN flagged for governance watch — CFO departure, J Capital short report
- Thesis intact (backlog $1.3B, 58% YoY revenue) but do not add until stabilized
- LOAR showing WEAK in screener — monitoring
- CW down 20% from cost — thesis review pending

## [1.9] — August 2026

### Portfolio Updates
- Added to PLTR position — 0.2864 shares @ $175.68
- Total PLTR position: 0.5427 shares @ $165.60 blended avg cost
- Portfolio fully deployed — $0 cash reserve
- 9 active positions across all 4 technology domains

### Dashboard Removed
- Streamlit Cloud dashboard discontinued
- Persistent yfinance rate limiting on cloud platforms made it 
  unreliable — broken more than working
- Replaced by GitHub Actions daily briefing (runs 9am ET weekdays)
- Daily briefing readable on iPhone via GitHub mobile
- Workflow: read briefing on bus → discuss here → execute via Robinhood Agentic

### Infrastructure
- Removed screener/dashboard.py
- Removed Schwab API dependency — reverted to yfinance locally
- Daily briefing GitHub Action remains operational

## [1.8] — August 2026

### Daily Briefing Automation
- Added GitHub Action — daily_briefing.yml
- Runs weekdays at 9am ET automatically
- Generates briefing markdown and commits to logs/
- Readable on iPhone via GitHub mobile
- Uses Schwab API credentials from repository secrets
- Manual trigger available via Actions tab

## [1.7] — August 2026

### Data Source — Schwab API
- Replaced Tradier with Schwab Developer API for price data
- Schwab provides reliable data with no rate limiting
- OAuth2 authentication via token.json locally
- Refresh token stored in Streamlit secrets for cloud deployment
- 12/12 tickers fetching clean via Schwab

### Dashboard — Restored
- Streamlit Cloud dashboard fully operational
- All sections working: posture, observations, scores, signals, portfolio
- Universe Posture: BULLISH as of August 4 2026

### Notable Events
- PLTR +29.5% on blowout Q2 earnings — revenue +93% YoY
- U.S. commercial revenue +149% YoY
- Full-year 2026 guidance raised to $8.15B
- Gap alert system correctly flagged PLTR — wait for pullback

## [1.6] — July 2026

### Universe Changes
- Removed VELO (Velo3D) — composite score fell below 35 removal 
  trigger for consecutive weeks. Pre-profitability, extreme 
  volatility, weak thesis fit confirmed.
- Added CW (Curtiss-Wright Corporation) — defense electronics, 
  naval nuclear systems, motion control. Q1 2026 EPS +23% YoY, 
  revenue +13%. Strong picks-and-shovels fit.
- Universe remains at 12 tickers
- CW thesis score: 80 | Fundamental score: 92 | Debut rank: #7

## [1.5] — July 2026

### Gap Alert System
- Added day-over-day % change calculation to signals.py
- Added gap flag logic — flags moves >= 5% in either direction
- Score.py now modifies action text for STRONG signals with gap flags
  e.g. "Consider adding — GAP DOWN -6.4% — monitor support"
- Report.py now surfaces gap alerts as a dedicated section
- First live alerts: MTRN -6.4% gap down, AVAV +10.7% gap up (July 3)

### Universe Cleanup
- Removed SXI (Standex International) — insufficient defense thesis fit
- Universe now 12 tickers
- Added VELO removal triggers to UNIVERSE.md

## [1.4] — July 2026

### Universe — SXI Removed
- Removed Standex International (SXI) from active universe
- Rationale: Insufficient defense thesis concentration — too 
  diversified across non-defense markets to justify inclusion
- Thesis score was 45 — lowest in universe by wide margin
- Discovery scanner will surface SXI again if defense revenue 
  mix changes significantly
- Universe now 12 tickers

## [1.3] — June 2026

### Fundamentals Cache — Fully Automated
- Added cache_fundamentals.py — saves fundamentals to JSON
- Updated fundamentals.py — reads from cache on cloud
- Added GitHub Action — auto-refreshes cache every Sunday at 2am UTC
- Dashboard fundamentals now work on Streamlit Cloud
- No manual intervention required for quarterly updates

### Portfolio Tracker
- Added portfolio.py — roster management system
- Identifies bench players with STRONG signals not currently held
- Added portfolio section to Streamlit dashboard
- Agentic account (••••5038) tracking foundation in place

### Story
- Added docs/STORY.md — project origin narrative

## [1.2] — June 2026

### Dashboard — Fixed for Streamlit Cloud
- Switched price data source from yfinance to Tradier API
- Tradier token read from Streamlit secrets for cloud deployment
- Fixed python-dotenv typo in requirements.txt
- Dashboard now fully operational on iPhone via Streamlit Cloud

### Discovery Module — v0.1
- Added discovery.py — automated candidate scanner
- ETF holdings scanner (ITA, XAR, DFEN)
- SEC EDGAR keyword scanner
- First run surfaced 9 candidates:
  - Added TDG, CW, HXL to watchlist in UNIVERSE.md
  - Eliminated GE (too large), ACHR (wrong sector)
  - RKLB, LUNR already known quantities

### Intelligence Module — v0.2
- Fixed Congress.gov API integration with API key
- Fixed SEC EDGAR headers error
- Fixed Shield AI query false positives
- Anduril and Shield AI confirmed still private as of June 2026

## [1.1] — June 2026

### Intelligence Module — v0.1 Complete
- Added intelligence.py — automated public data monitoring
- Pentagon contracts: Defense.gov RSS feed monitoring for 
  universe company mentions
- Congress.gov NDAA: API-based keyword monitoring for 
  thesis-relevant defense legislation keywords
- SEC EDGAR: IPO watchlist monitoring for Anduril and 
  Shield AI S-1 filings
- All alerts require manual review — nothing changes 
  automatically
- Congress.gov API key required (stored in .env, 
  never committed to GitHub)
- Current status: Anduril and Shield AI confirmed 
  still private as of June 2026
- Added python-dotenv to requirements.txt

## [1.0] — June 2026

### Backtest — 13-Ticker Universe
- Reran backtest against full expanded 13-ticker universe
- New additions validated:
  - PLTR: 47.9% win rate, 193% total return, 144% best trade
  - AXON: 42.5% win rate, 157% total return, 63% best trade
- Consistent findings confirmed across all backtest runs:
  - KTOS: strongest signal performer (195% total)
  - HEI: consistently poor technical signals (-20% total)
  - KRMN: best win rate (62.5%) despite current bearish trend
- Universe now at v1.0 milestone — thesis documented, 
  universe defined, screener operational, backtest complete

### Version milestone
- Project reaches v1.0 — all Phase 1 and Phase 2 
  objectives complete
- Phase 3 begins: dashboard fix, Robinhood execution 
  integration, rebalancing shock trigger

## [0.9] — June 2026

### Universe — Major Expansion (v0.3)
- Added PLTR (Palantir Technologies) — AI/Autonomy, special 
  case exception, thesis score 85
- Added AXON (Axon Enterprise) — IoMT/Digital Battlefield, 
  dual-domain, thesis score 75
- Restructured into four technology domains:
  - AI & Autonomy (PLTR, AVAV, KTOS)
  - Hypersonic, Space & Propulsion (KRMN, HWM, ATI)
  - IoMT, Sensors & Digital Battlefield (AXON, TDY, HEI, LOAR)
  - Industrial Supply Chain & Materials (SXI, MTRN, VELO)
- Added tier definitions: Disruptor, Standard, Anchor
- Added IPO watchlist: Anduril, Shield AI
- Added cash runway removal trigger (2 year minimum)
- Added rebalancing shock trigger (>13.5% / <6.5%)
- Added valuation risk flags for PLTR and KRMN
- Watchlist: FLY, AADX, BAH

### Thesis — v0.2
- Expanded technology domains to include IoMT, Quantum, 
  AI/Autonomy
- Added tier framework (Disruptor 75% / Standard 15% / Anchor 10%)
- Added special case exception rule for PLTR
- Added Valley of Death risk and IPO watch section

### Screener
- universe.py updated to 13 tickers with sector classification
- score.py updated with PLTR (85) and AXON (75) thesis overrides
- 13/13 tickers pulling clean data

## [0.8] — June 2026

### Backtest — 5y Period Analysis
- Reran backtest with 5y period for more robust results
- Key findings confirmed across both 2y and 5y periods:
  - KTOS and KRMN: strongest technical signal performance
  - HEI: consistently poor technical signals (31.2% win rate)
  - TDY and MTRN: technical signals nearly breakeven
- VELO pre-split price artifacts noted in 2021-2023 data
  — trades from that period unreliable
- Conclusion: technical signals most reliable on pure
  hypersonics names, less reliable on larger stable names
- HEI scores STRONG fundamentally but technical entry
  timing historically poor — confirmed across both periods

## [0.7] — June 2026

### Backtest — Initial Run Complete
- Added backtest.py — technical signal backtest over 2y period
- Buy threshold: 60, Sell threshold: 45
- Key findings:
  - KTOS: 63.6% win rate, 13.8% avg return — strongest signal
  - KRMN: 62.5% win rate, 10.07% avg return — solid signal
  - HEI: 24.1% win rate, -0.91% avg return — signals unreliable
  - LOAR: 33.3% win rate, -1.23% avg return — signals unreliable
- HEI scores STRONG fundamentally but technical signals 
  historically poor — warrants caution on entry timing
- Documented limitations: technical only, survivorship bias,
  no transaction costs, past performance caveat
  
## [0.6] — June 2026

### Screener — Phase 2 Complete
- Integrated real fundamental scoring replacing placeholder 50.0
- Added thesis score overrides for all 11 universe tickers
- Fixed Windows encoding issue in report.py
- Updated report disclaimer to reflect Phase 2 status
- Three-component scoring now fully operational:
  - Technical: real signal data
  - Fundamental: real yfinance data
  - Thesis: manually set per investment thesis alignment
- Current STRONG signals: HEI (79.0), HWM (76.8), LOAR (75.0)
- Current WEAK/NEUTRAL of concern: KRMN (53.8), VELO (56.8)

## [0.5] — June 2026

### Screener — Report Output
- Updated report.py to generate professional markdown output
- Added dated briefing files saved automatically to logs folder
- Fixed Windows encoding issue with emoji characters
- Format: headers, tables, narrative observations, disclaimer
- Preview in VS Code with Ctrl+Shift+V
-
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
