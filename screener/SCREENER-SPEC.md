# Hypersonic Defense Screener — Screener Specification

**Version:** 0.1  
**Date:** June 2026  
**Status:** Draft  

---

## 1. Purpose

The screener evaluates every ticker in the defined 
universe on a regular basis and produces a ranked, 
scored output indicating the relative strength and 
signal status of each position. It is designed to 
support disciplined, thesis-driven buy, hold, and 
trim decisions — not to generate high-frequency 
trading signals.

---

## 2. Design Principles

- **Thesis-first:** Every signal must be justifiable 
  against the investment thesis. No signal is included 
  purely because it is technically popular.
- **Transparency:** Every score and signal must be 
  explainable in plain English. No black boxes.
- **Simplicity over complexity:** A simple, robust 
  signal beats a complex, fragile one.
- **Human override:** The screener informs decisions. 
  It does not make them. Final judgment always rests 
  with the investor.
- **Honest output:** The screener must surface 
  weakness as clearly as it surfaces strength.

---

## 3. Input Data

### Universe
All tickers defined in UNIVERSE.md at time of run.

### Data Sources (Phase 1)
- **yfinance** — price data, volume, basic fundamentals
- **Manual inputs** — contract wins, program news, 
  thesis-relevant events not captured by price data

### Data Sources (Future Phases)
- SEC EDGAR — earnings, filings, insider activity
- Defense contract databases — USASpending.gov
- News sentiment — defense-specific publications

### Data Frequency
- **Price/technical signals:** Daily
- **Fundamental signals:** Quarterly (earnings cycle)
- **Manual thesis inputs:** As events occur

---

## 4. Signal Framework

### 4.1 Technical Signals

| Signal | Indicator | Rationale |
|--------|-----------|-----------|
| Trend | Price vs MA50, MA200 | Is the stock in an uptrend or downtrend? |
| Momentum | RSI (14-day) | Overbought or oversold conditions |
| Volume | Volume vs 20-day avg | Confirms price moves with conviction |
| Moving Average Cross | MA20 vs MA50 | Short-term momentum shift detection |
| Relative Strength | Price vs universe average | Which names are leading vs lagging? |

### 4.2 Fundamental Signals

| Signal | Metric | Rationale |
|--------|--------|-----------|
| Revenue Growth | YoY revenue change | Is the business growing? |
| Backlog | Funded backlog trend | Forward revenue visibility |
| Margin Trend | Gross and operating margin | Is growth profitable? |
| Defense Revenue Mix | % revenue from defense | Thesis relevance maintenance |

### 4.3 Thesis Signals (Manual)
These are qualitative inputs that override or 
weight quantitative signals:

| Signal | Trigger | Impact |
|--------|---------|--------|
| Contract Win | Major hypersonics/defense contract awarded | Positive weight |
| Contract Loss | Key program cancelled or lost | Negative weight / removal review |
| Program Milestone | DoD program advances to next phase | Positive weight |
| Acquisition Risk | Rumored or announced acquisition by prime | Removal review |
| Foreign Adversary Flag | Federal investigation opened | Immediate removal review |

---

## 5. Scoring Methodology

### Composite Score
Each ticker receives a composite score from 0-100 
built from weighted signal categories:

| Category | Weight | Rationale |
|----------|--------|-----------|
| Technical | 40% | Price action reflects real-time market sentiment |
| Fundamental | 40% | Business quality and growth trajectory |
| Thesis | 20% | Qualitative alignment with investment thesis |

### Score Interpretation
| Score Range | Interpretation | Action Guidance |
|-------------|---------------|-----------------|
| 75-100 | Strong | Consider initiating or adding |
| 50-74 | Neutral | Hold; monitor for direction |
| 25-49 | Weak | Consider trimming; review thesis fit |
| 0-24 | Critical | Review for removal from universe |

---

## 6. Output

### Primary Output
A ranked table of all universe tickers updated daily:

### Secondary Output
- Signal change alerts — when a ticker crosses a 
  score threshold in either direction
- Universe health summary — overall posture of 
  the universe (bullish / neutral / bearish)
- Individual ticker detail report on request

---

## 7. Position Sizing Integration

The screener output feeds position sizing as follows:

- **Score 75-100:** Eligible for full position 
  (up to maximum allocation per ticker)
- **Score 50-74:** Eligible for half position
- **Score 25-49:** Existing positions only — 
  no additions
- **Score 0-24:** Review for exit

### Maximum Allocations (to be refined)
- Maximum single ticker: 20% of portfolio
- Maximum single domain: 40% of portfolio
- Minimum cash reserve: 10% of portfolio

---

## 8. Run Schedule

| Task | Frequency |
|------|-----------|
| Price data refresh | Daily (market close) |
| Score recalculation | Daily (after data refresh) |
| Fundamental update | Quarterly (post-earnings) |
| Thesis signal review | Weekly minimum |
| Universe review | Quarterly |

---

## 9. Technology Stack

| Component | Tool | Rationale |
|-----------|------|-----------|
| Language | Python 3.x | Consistent with existing scanner work |
| Data | yfinance | Free, reliable, sufficient for Phase 1 |
| Computation | pandas, numpy | Standard data manipulation |
| Notebook | Jupyter | Development and testing environment |
| IDE | VS Code | Primary development environment |
| Version Control | GitHub (private) | Already established |
| Visualization | matplotlib / plotly | Signal charts and dashboard |
| Future dashboard | Streamlit | Mobile-accessible monitoring |

---

## 10. Phased Development Plan

### Phase 1 — Core Screener (Current)
- Price and technical signal calculation
- Basic composite scoring
- CSV output
- Manual thesis signal input

### Phase 2 — Fundamentals Integration
- Earnings data integration
- Backlog and defense revenue tracking
- Automated fundamental scoring

### Phase 3 — Alerts and Automation
- Signal change notifications
- Scheduled automated runs
- Robinhood MCP execution integration

### Phase 4 — Dashboard
- Streamlit dashboard
- Mobile-accessible interface
- Autopilot Pilot documentation package

---

## 11. Limitations and Honest Caveats

- **yfinance data quality:** Free data has gaps and 
  occasional errors. Results must be sanity-checked.
- **Backtest survivorship bias:** Historical testing 
  will only include companies that survived. 
  This overstates historical performance.
- **Thesis signals are subjective:** Manual inputs 
  introduce human bias. Document every input.
- **Small universe:** 11 tickers plus watchlist is 
  a small sample. Signals may be noisy.
- **This is not a prediction engine.** It is a 
  decision-support tool.

---

## Version History

| Version | Date | Notes |
|---------|------|-------|
| 0.1 | June 2026 | Initial specification |
