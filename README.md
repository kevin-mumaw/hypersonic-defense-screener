# Second Layer Capital — Hypersonic Defense Screener

A rules-based stock screening and portfolio management system 
targeting the picks-and-shovels supply chain of next-generation 
defense technology — hypersonic weapons, directed energy, 
autonomous systems, and advanced propulsion.

Built by a 21-year U.S. Army veteran (Signal Corps, Infantry, 
Civil Affairs) with a background in cybersecurity and critical 
program protection.

---

## Thesis

The United States and its allies are entering a sustained period 
of next-generation weapons development driven by peer competitor 
threats from China and Russia. The supply chain beneath these 
programs — propulsion manufacturers, advanced materials suppliers, 
guidance systems makers, thermal protection specialists, and systems 
integrators — will see durable, multi-decade government contract 
flow regardless of which specific platforms win.

This screener targets that picks-and-shovels layer, not the prime 
contractors.

---

## Universe

13 actively screened tickers across four technology domains:

- **AI & Autonomy** — PLTR, AVAV, KTOS
- **Hypersonic, Space & Propulsion** — KRMN, HWM, ATI
- **IoMT & Digital Battlefield** — AXON, TDY, HEI, LOAR
- **Industrial Supply Chain** — SXI, MTRN, VELO

---

## Scoring System

Each ticker receives a composite score (0-100) built from three components:

| Component | Weight | Source |
|-----------|--------|--------|
| Technical | 40% | Price data via Tradier API |
| Fundamental | 40% | Revenue growth, margins, D/E via yfinance |
| Thesis | 20% | Manual alignment score |

---

## Active Portfolio

Live paper portfolio managed via Robinhood Agentic account.
Current positions: HWM, HEI, LOAR, AXON

---

## Dashboard

The Streamlit Cloud deployment has been discontinued due to 
persistent platform instability — rate limiting, credential 
failures, and segfaults on the free tier made it unreliable 
for production use.

The dashboard runs correctly in local development:
```bash
streamlit run screener/dashboard.py
```

A more robust deployment solution is under evaluation.

---

## Status
🟢 Active — Phase 2 complete, live trading initiated June 2026

## Structure
/thesis      — Investment thesis and rationale

/universe    — Ticker universe and screening criteria

/screener    — Scoring, signals, fundamentals, portfolio tracking

/backtest    — Backtesting methodology and results

/data        — Cached fundamental data

/docs        — CHANGELOG, STORY, screener specification

/logs        — Daily briefings, intelligence, discovery reports

.github      — Automated workflows (weekly fundamentals refresh)

## Social
- X: [@SecondLayerCap](https://x.com/SecondLayerCap)

---

## Disclaimer
This project is for personal research and educational purposes only.
Nothing here constitutes financial advice.
