# discovery.py
# Scans for potential new universe candidates outside current holdings
# Sources: Defense ETF holdings (ITA, XAR, DFEN), SEC EDGAR keyword search
# Output: Candidate list saved to logs/discovery_YYYY-MM-DD.md
# All candidates require manual research before adding to universe

import requests
import json
import time
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from universe import UNIVERSE

# --- Configuration ---

# ETFs to scan
DEFENSE_ETFS = ["ITA", "XAR", "DFEN"]

# Prime contractors to exclude
PRIME_CONTRACTORS = [
    "LMT", "RTX", "NOC", "GD", "BA", "HII", "L3H", "LHX",
    "LDOS", "BAH", "SAIC", "CACI", "MANT", "DRS"
]

# Current universe tickers to exclude
CURRENT_UNIVERSE = list(UNIVERSE.keys())

# SEC EDGAR thesis keywords
THESIS_KEYWORDS = [
    "hypersonic",
    "directed energy",
    "loitering munition",
    "autonomous systems",
    "unmanned aerial",
    "space force",
    "counter-drone",
]

# Minimum market cap to consider ($500M)
MIN_MARKET_CAP = 500_000_000


# --- ETF Holdings Scanner ---

def get_etf_holdings(etf_ticker):
    """
    Fetch ETF holdings using yfinance.
    Returns list of ticker symbols in the ETF.
    """
    try:
        import yfinance as yf
        etf = yf.Ticker(etf_ticker)
        holdings = etf.funds_data
        
        if holdings is None:
            return []
            
        # Try to get top holdings
        top_holdings = holdings.top_holdings
        if top_holdings is not None and not top_holdings.empty:
            return list(top_holdings.index)
            
        return []
        
    except Exception as e:
        print(f"  WARNING: Could not fetch {etf_ticker} holdings: {e}")
        return []


def scan_etf_holdings():
    """
    Scan defense ETF holdings for candidates not in current universe.
    
    Returns:
        list of candidate dicts
    """
    print("Scanning defense ETF holdings...")
    candidates = []
    seen = set()

    for etf in DEFENSE_ETFS:
        print(f"  Fetching {etf} holdings...")
        holdings = get_etf_holdings(etf)
        
        if not holdings:
            print(f"  WARNING: No holdings data for {etf}")
            continue
            
        print(f"  {etf}: {len(holdings)} holdings found")
        
        for ticker in holdings:
            # Skip if already in universe
            if ticker in CURRENT_UNIVERSE:
                continue
            # Skip prime contractors
            if ticker in PRIME_CONTRACTORS:
                continue
            # Skip duplicates across ETFs
            if ticker in seen:
                continue
                
            seen.add(ticker)
            candidates.append({
                "ticker" : ticker,
                "source" : f"ETF: {etf}",
                "reason" : f"Appears in {etf} defense ETF — not in current universe",
            })

        time.sleep(0.5)

    return candidates


# --- SEC EDGAR Keyword Scanner ---

def scan_edgar_keywords():
    """
    Search SEC EDGAR for recent filings containing thesis keywords.
    Returns companies not already in universe.
    
    Returns:
        list of candidate dicts
    """
    print("\nScanning SEC EDGAR for thesis keywords...")
    candidates = []
    seen = set()

    headers = {
        "User-Agent": "hypersonic-defense-screener research@example.com"
    }

    for keyword in THESIS_KEYWORDS:
        print(f"  Searching: '{keyword}'...")
        
        url = "https://efts.sec.gov/LATEST/search-index"
        params = {
            "q"       : f'"{keyword}"',
            "forms"   : "10-K,10-Q",
            "dateRange": "custom",
            "startdt" : f"{date.today().year - 1}-01-01",
            "enddt"   : date.today().strftime("%Y-%m-%d"),
        }

        try:
            response = requests.get(url, params=params,
                                   headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            hits = data.get("hits", {}).get("hits", [])

            for hit in hits[:10]:
                source      = hit.get("_source", {})
                entity_name = source.get("entity_name", "")
                ticker      = source.get("ticker_symbol", "")
                file_date   = source.get("file_date", "")

                if not ticker:
                    continue
                if ticker in CURRENT_UNIVERSE:
                    continue
                if ticker in PRIME_CONTRACTORS:
                    continue
                if ticker in seen:
                    continue

                seen.add(ticker)
                candidates.append({
                    "ticker"  : ticker,
                    "company" : entity_name,
                    "source"  : "SEC EDGAR 10-K/10-Q",
                    "reason"  : f"Filing contains keyword: '{keyword}' (filed {file_date})",
                })

        except Exception as e:
            print(f"  WARNING: EDGAR search failed for '{keyword}': {e}")

        time.sleep(0.5)

    return candidates


# --- Market Cap Filter ---

def filter_by_market_cap(candidates):
    """
    Filter candidates by minimum market cap.
    Removes penny stocks and micro caps.
    
    Returns:
        list of candidates with market cap data added
    """
    import yfinance as yf

    print(f"\nFiltering {len(candidates)} candidates by market cap...")
    filtered = []

    for candidate in candidates:
        try:
            ticker = candidate["ticker"]
            info   = yf.Ticker(ticker).info
            mktcap = info.get("marketCap", 0)
            name   = info.get("shortName", candidate.get("company", ticker))
            exchange = info.get("exchange", "Unknown")

            if mktcap and mktcap >= MIN_MARKET_CAP:
                candidate["company"]    = name
                candidate["market_cap"] = mktcap
                candidate["exchange"]   = exchange
                filtered.append(candidate)
                print(f"  {ticker:<6} — ${mktcap/1e9:.1f}B — {name}")
            else:
                print(f"  {ticker:<6} — below minimum market cap, skipped")

            time.sleep(0.3)

        except Exception as e:
            print(f"  {candidate['ticker']:<6} — could not fetch market cap: {e}")

    return filtered


# --- Report Generator ---

def generate_discovery_report(etf_candidates, edgar_candidates):
    """
    Generate markdown discovery report.
    """
    today = date.today().strftime("%B %d, %Y")
    lines = []

    lines.append("# Hypersonic Defense Screener — Discovery Report")
    lines.append(f"## {today}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("> **Manual research required for all candidates.**")
    lines.append("> Do not add to universe without verifying:")
    lines.append("> 1. Publicly traded on US exchange")
    lines.append("> 2. Fits picks-and-shovels thesis")
    lines.append("> 3. Not a prime contractor")
    lines.append("> 4. Sufficient liquidity")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ETF candidates
    lines.append("## ETF Holdings Candidates")
    lines.append("")
    lines.append(f"*Companies in ITA, XAR, or DFEN not in current universe*")
    lines.append("")

    if etf_candidates:
        lines.append("| Ticker | Company | Market Cap | Exchange | Source |")
        lines.append("|--------|---------|------------|----------|--------|")
        for c in sorted(etf_candidates,
                       key=lambda x: x.get("market_cap", 0),
                       reverse=True):
            mktcap = f"${c.get('market_cap', 0)/1e9:.1f}B"
            lines.append(
                f"| {c['ticker']} "
                f"| {c.get('company', 'Unknown')} "
                f"| {mktcap} "
                f"| {c.get('exchange', 'Unknown')} "
                f"| {c['source']} |"
            )
    else:
        lines.append("> No ETF candidates found above minimum market cap.")

    lines.append("")
    lines.append("---")
    lines.append("")

    # EDGAR candidates
    lines.append("## SEC EDGAR Keyword Candidates")
    lines.append("")
    lines.append(f"*Companies filing 10-K/10-Q mentioning thesis keywords*")
    lines.append("")

    if edgar_candidates:
        lines.append("| Ticker | Company | Market Cap | Reason |")
        lines.append("|--------|---------|------------|--------|")
        for c in sorted(edgar_candidates,
                       key=lambda x: x.get("market_cap", 0),
                       reverse=True):
            mktcap = f"${c.get('market_cap', 0)/1e9:.1f}B"
            lines.append(
                f"| {c['ticker']} "
                f"| {c.get('company', 'Unknown')} "
                f"| {mktcap} "
                f"| {c['reason']} |"
            )
    else:
        lines.append("> No EDGAR candidates found above minimum market cap.")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Next Steps")
    lines.append("")
    lines.append("For each candidate above:")
    lines.append("")
    lines.append("1. Research the company's defense revenue mix")
    lines.append("2. Confirm picks-and-shovels fit vs prime contractor")
    lines.append("3. Check recent earnings and backlog")
    lines.append("4. If qualified, add to `universe/UNIVERSE.md` watchlist")
    lines.append("5. Update `screener/universe.py` and `screener/score.py`")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated by Hypersonic Defense Screener — {today}*")

    return "\n".join(lines)


def save_discovery_report(markdown):
    """Save discovery report to logs folder."""
    today    = date.today().strftime("%Y-%m-%d")
    filename = f"discovery_{today}.md"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root  = os.path.dirname(script_dir)
    logs_dir   = os.path.join(repo_root, "logs")
    filepath   = os.path.join(logs_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"\nDiscovery report saved: logs/{filename}")
    return filepath


def run_discovery():
    """
    Run full discovery scan and generate report.
    """
    print("=" * 55)
    print("Hypersonic Defense Screener — Discovery Scan")
    print(f"Date: {date.today().strftime('%B %d, %Y')}")
    print("=" * 55)
    print()

    # ETF scan
    etf_raw        = scan_etf_holdings()
    etf_filtered   = filter_by_market_cap(etf_raw)

    # EDGAR scan
    edgar_raw      = scan_edgar_keywords()
    edgar_filtered = filter_by_market_cap(edgar_raw)

    # Generate report
    markdown = generate_discovery_report(etf_filtered, edgar_filtered)
    save_discovery_report(markdown)

    print("\n")
    print(markdown)

    total = len(etf_filtered) + len(edgar_filtered)
    print(f"\nTotal candidates found: {total}")
    print("Manual research required before adding any to universe.")

    return etf_filtered, edgar_filtered


if __name__ == "__main__":
    run_discovery()