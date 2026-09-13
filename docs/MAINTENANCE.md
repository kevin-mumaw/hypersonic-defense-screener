# Second Layer Capital — Maintenance Checklist

---

## Daily (5 minutes — on the bus)

- [ ] Open GitHub on iPhone → `logs/` → read today's `briefing_YYYY-MM-DD.md`
- [ ] Check Universe Posture
- [ ] Check Gap Alerts — any names that surged or crashed overnight
- [ ] Note anything needing action — bring to Claude if so

*The GitHub Action runs this automatically at midnight ET weekdays.*

---

## Weekly (Sunday evening — 30-45 minutes)

### Run locally:
```bash
cd C:\projects\hypersonic-defense-scanner\hypersonic-defense-screener
venv\Scripts\activate
git pull origin main
```

### Screener:
```bash
python screener/report.py
```
- [ ] Review Universe Posture
- [ ] Review Composite Scores — any new STRONG or WEAK signals?
- [ ] Review Gap Alerts
- [ ] Commit briefing log

### Rebalancing:
```bash
python screener/execute_rebalance.py
```
- [ ] Review shock triggers — any >13.5% or <6.5%?
- [ ] Review drift conditions — any approaching 30 days?
- [ ] Execute only if shock trigger AND thesis supports it
- [ ] Update `positions.py` if any trades executed

### Discovery:
```bash
python screener/discovery.py
```
- [ ] Review new ETF candidates
- [ ] Add qualified names to `UNIVERSE.md` watchlist

### Intelligence:
```bash
python screener/intelligence.py
```
- [ ] Review Pentagon contract alerts
- [ ] Review NDAA keyword alerts
- [ ] Check Anduril and Shield AI IPO status

### Signal History:
```bash
python screener/signal_history.py
```
- [ ] Review 30-day score trends
- [ ] Flag any names WEAK for 10+ consecutive days

### Commit everything:
```bash
git add -A
git commit -m "Weekly maintenance YYYY-MM-DD"
git push
```

---

## Monthly (first Sunday of month — 60-90 minutes)

### Backtest:
```bash
cd backtest
python backtest.py
cd ..
```
- [ ] Compare win rates to previous run
- [ ] Flag any names with deteriorating signal reliability
- [ ] Update backtest findings in CHANGELOG

### Fundamentals cache refresh:
```bash
python screener/cache_fundamentals.py
git add -f data/fundamentals_cache.json
git commit -m "Refresh fundamentals cache YYYY-MM"
git push
```
- [ ] Review fundamental score changes
- [ ] Update thesis score overrides in `score.py` if warranted

### Thesis review — each held position:
- [ ] Is the original buy thesis still intact?
- [ ] Has anything changed materially — earnings, contracts, management?
- [ ] Decision: Buy more / Hold / Trim / Exit
- [ ] Document decision in CHANGELOG

### Universe review:
- [ ] Any watchlist names ready for promotion to active universe?
- [ ] Any active names approaching removal triggers?
- [ ] Update `UNIVERSE.md` and `universe.py` if changes made

### Social media:
```bash
python screener/social.py
```
- [ ] Generate monthly performance post
- [ ] Review and post to X and LinkedIn if appropriate

---

## Quarterly

- [ ] Full STORY.md update — add new milestones and decisions
- [ ] Performance vs S&P 500 and ITA/XAR ETF benchmarks
- [ ] THESIS.md review — has the macro thesis evolved?
- [ ] Evaluate Autopilot Pilot readiness (target: March 2027)

---

## As Needed

- [ ] After every trade → update `positions.py` and commit
- [ ] After earnings → check thesis score overrides in `score.py`
- [ ] After major news → run screener, discuss with Claude, decide action
- [ ] When Schwab token expires → refresh `token.json` from weekly-options-signal-engine

---

## Emergency Checklist (Market Crisis)

- [ ] Run screener immediately
- [ ] Check if any shock triggers fired
- [ ] Research cause — thesis deterioration vs market selloff?
- [ ] Do NOT rebalance during acute selloff without 30-day buffer
- [ ] Document the event and decision in CHANGELOG
- [ ] Hold unless fundamental thesis is broken

---

*Last updated: September 2026*
