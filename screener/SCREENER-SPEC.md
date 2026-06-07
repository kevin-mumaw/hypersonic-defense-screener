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
