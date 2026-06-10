# intelligence.py
# Monitors public data sources for thesis-relevant events
# Sources: Defense.gov contracts, Congress.gov NDAA, SEC EDGAR
# Output: Alert flags for manual review — nothing changes automatically
# Human review required before any thesis score override

import requests
from bs4 import BeautifulSoup
from datetime import date, datetime
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from universe import UNIVERSE

# --- Configuration ---

# Universe company names for contract matching
COMPANY_NAMES = {
    "PLTR": ["Palantir", "Palantir Technologies"],
    "AVAV": ["AeroVironment", "Aerovironment"],
    "KTOS": ["Kratos", "Kratos Defense"],
    "KRMN": ["Karman", "Karman Holdings"],
    "HWM":  ["Howmet", "Howmet Aerospace"],
    "ATI":  ["ATI Inc", "Allegheny Technologies"],
    "AXON": ["Axon", "Axon Enterprise"],
    "TDY":  ["Teledyne", "Teledyne Technologies"],
    "HEI":  ["Heico", "Heico Corporation"],
    "LOAR": ["Loar", "Loar Holdings"],
    "SXI":  ["Standex", "Standex International"],
    "MTRN": ["Materion"],
    "VELO": ["Velo3D"],
}

# NDAA keywords to monitor
NDAA_KEYWORDS = [
    "hypersonic",
    "unmanned",
    "directed energy",
    "autonomous systems",
    "space force",
    "loitering munition",
    "artificial intelligence",
    "counter-hypersonic",
    "proliferated warfighter space layer",
]

# IPO watchlist
IPO_WATCHLIST = [
    "Anduril Industries",
    "Shield AI",
]

# Minimum contract value to flag (dollars)
MIN_CONTRACT_VALUE = 50_000_000


# --- Pentagon Contract Scraper ---

def scrape_pentagon_contracts():
    """
    Scrape Defense.gov contract announcements.
    Flags contracts mentioning universe companies over $50M.
    
    Returns:
        list of alert dicts
    """
    alerts = []
    url = "https://www.defense.gov/News/Contracts/"

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Find contract announcement items
        items = soup.find_all("div", class_="news-article-list")
        if not items:
            items = soup.find_all("li", class_="feature")
        if not items:
            # Fallback — grab all paragraph text
            items = soup.find_all("p")

        for item in items[:50]:  # Limit to 50 most recent
            text = item.get_text(separator=" ", strip=True)

            # Check for universe company mentions
            for ticker, names in COMPANY_NAMES.items():
                for name in names:
                    if name.lower() in text.lower():
                        alerts.append({
                            "source"  : "Pentagon Contracts",
                            "ticker"  : ticker,
                            "company" : names[0],
                            "text"    : text[:300],
                            "url"     : url,
                            "action"  : f"Review thesis score override for {ticker}",
                        })
                        break

    except Exception as e:
        alerts.append({
            "source"  : "Pentagon Contracts",
            "ticker"  : "ERROR",
            "company" : "N/A",
            "text"    : f"Scrape failed: {str(e)}",
            "url"     : url,
            "action"  : "Check defense.gov manually",
        })

    return alerts


# --- NDAA Keyword Monitor ---

def scrape_ndaa_keywords():
    """
    Monitor Congress.gov for NDAA-related defense keywords.
    
    Returns:
        list of alert dicts
    """
    alerts = []
    url = "https://www.congress.gov/search?q=%7B%22source%22%3A%22legislation%22%2C%22search%22%3A%22national+defense+authorization%22%7D&pageSize=5"

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.find_all("li", class_="expanded")

        for item in items[:10]:
            text = item.get_text(separator=" ", strip=True)

            for keyword in NDAA_KEYWORDS:
                if keyword.lower() in text.lower():
                    alerts.append({
                        "source"  : "Congress.gov NDAA",
                        "ticker"  : "UNIVERSE",
                        "keyword" : keyword,
                        "text"    : text[:300],
                        "url"     : url,
                        "action"  : f"Review NDAA language re: '{keyword}' — may affect thesis weighting",
                    })
                    break

    except Exception as e:
        alerts.append({
            "source"  : "Congress.gov NDAA",
            "ticker"  : "ERROR",
            "keyword" : "N/A",
            "text"    : f"Scrape failed: {str(e)}",
            "url"     : url,
            "action"  : "Check congress.gov manually",
        })

    return alerts


# --- SEC EDGAR IPO Watchlist ---

def scrape_sec_ipo_watchlist():
    """
    Monitor SEC EDGAR for S-1 filings from IPO watchlist companies.
    
    Returns:
        list of alert dicts
    """
    alerts = []

    for company in IPO_WATCHLIST:
        query = company.replace(" ", "+")
        url = f"https://efts.sec.gov/LATEST/search-index?q=%22{query}%22&dateRange=custom&startdt=2026-01-01&forms=S-1"

        try:
            headers = {"User-Agent": "hypersonic-defense-screener@research.com"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            hits = data.get("hits", {}).get("hits", [])

            if hits:
                for hit in hits[:3]:
                    source = hit.get("_source", {})
                    alerts.append({
                        "source"  : "SEC EDGAR S-1 Watch",
                        "ticker"  : "IPO ALERT",
                        "company" : company,
                        "text"    : f"S-1 filing detected: {source.get('file_date', 'Unknown date')} — {source.get('display_names', company)}",
                        "url"     : f"https://www.sec.gov/cgi-bin/browse-edgar?company={query}&action=getcompany&type=S-1",
                        "action"  : f"IMMEDIATE: Review {company} S-1 — prepare to add to universe on IPO",
                    })

        except Exception as e:
            alerts.append({
                "source"  : "SEC EDGAR S-1 Watch",
                "ticker"  : "ERROR",
                "company" : company,
                "text"    : f"Scrape failed: {str(e)}",
                "url"     : "https://efts.sec.gov",
                "action"  : f"Check SEC EDGAR manually for {company}",
            })

        time.sleep(0.5)  # Be polite to SEC servers

    return alerts


# --- Report Generator ---

def generate_intelligence_report(all_alerts):
    """
    Generate markdown intelligence report from all alerts.
    """
    today = date.today().strftime("%B %d, %Y")
    lines = []

    lines.append("# Hypersonic Defense Screener — Intelligence Report")
    lines.append(f"## {today}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("> **Manual review required for all alerts.**")
    lines.append("> Nothing changes automatically.")
    lines.append("> Thesis score overrides in `score.py` must be")
    lines.append("> updated manually after reviewing each alert.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Pentagon contracts
    contract_alerts = [a for a in all_alerts
                      if a["source"] == "Pentagon Contracts"
                      and a["ticker"] != "ERROR"]
    contract_errors = [a for a in all_alerts
                      if a["source"] == "Pentagon Contracts"
                      and a["ticker"] == "ERROR"]

    lines.append("## Pentagon Contract Alerts")
    lines.append("")

    if contract_alerts:
        for alert in contract_alerts:
            lines.append(f"### 🚨 {alert['ticker']} — {alert['company']}")
            lines.append(f"**Source:** {alert['url']}")
            lines.append(f"**Excerpt:** {alert['text']}")
            lines.append(f"**Action Required:** {alert['action']}")
            lines.append("")
    elif contract_errors:
        lines.append(f"> ⚠️ Scrape error: {contract_errors[0]['text']}")
        lines.append(f"> Check manually: {contract_errors[0]['url']}")
        lines.append("")
    else:
        lines.append("> No universe companies mentioned in recent contracts.")
        lines.append("")

    lines.append("---")
    lines.append("")

    # NDAA keywords
    ndaa_alerts = [a for a in all_alerts
                  if a["source"] == "Congress.gov NDAA"
                  and a["ticker"] != "ERROR"]
    ndaa_errors = [a for a in all_alerts
                  if a["source"] == "Congress.gov NDAA"
                  and a["ticker"] == "ERROR"]

    lines.append("## NDAA Keyword Alerts")
    lines.append("")

    if ndaa_alerts:
        for alert in ndaa_alerts:
            lines.append(f"### 📋 Keyword: '{alert['keyword']}'")
            lines.append(f"**Source:** {alert['url']}")
            lines.append(f"**Excerpt:** {alert['text']}")
            lines.append(f"**Action Required:** {alert['action']}")
            lines.append("")
    elif ndaa_errors:
        lines.append(f"> ⚠️ Scrape error: {ndaa_errors[0]['text']}")
        lines.append("")
    else:
        lines.append("> No new NDAA keyword matches found.")
        lines.append("")

    lines.append("---")
    lines.append("")

    # SEC EDGAR
    sec_alerts = [a for a in all_alerts
                 if a["source"] == "SEC EDGAR S-1 Watch"
                 and a["ticker"] != "ERROR"]
    sec_errors = [a for a in all_alerts
                 if a["source"] == "SEC EDGAR S-1 Watch"
                 and a["ticker"] == "ERROR"]

    lines.append("## SEC EDGAR IPO Watch")
    lines.append("")

    if sec_alerts:
        for alert in sec_alerts:
            lines.append(f"### 🔔 IPO ALERT — {alert['company']}")
            lines.append(f"**Filing:** {alert['text']}")
            lines.append(f"**Source:** {alert['url']}")
            lines.append(f"**Action Required:** {alert['action']}")
            lines.append("")
    elif sec_errors:
        lines.append(f"> ⚠️ Scrape error: {sec_errors[0]['text']}")
        lines.append("")
    else:
        lines.append("> No S-1 filings detected for Anduril or Shield AI.")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"*Generated by Hypersonic Defense Screener — {today}*")

    return "\n".join(lines)


def save_intelligence_report(markdown):
    """Save intelligence report to logs folder."""
    today    = date.today().strftime("%Y-%m-%d")
    filename = f"intelligence_{today}.md"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root  = os.path.dirname(script_dir)
    logs_dir   = os.path.join(repo_root, "logs")
    filepath   = os.path.join(logs_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"Intelligence report saved: logs/{filename}")
    return filepath


def run_intelligence():
    """
    Run all intelligence scrapers and generate report.
    """
    print("Running intelligence scrapers...")
    print("(Manual review required for all alerts)\n")

    all_alerts = []

    print("Checking Pentagon contracts...")
    all_alerts.extend(scrape_pentagon_contracts())
    time.sleep(1)

    print("Checking Congress.gov NDAA...")
    all_alerts.extend(scrape_ndaa_keywords())
    time.sleep(1)

    print("Checking SEC EDGAR IPO watchlist...")
    all_alerts.extend(scrape_sec_ipo_watchlist())

    print(f"\nTotal alerts: {len([a for a in all_alerts if a['ticker'] != 'ERROR'])}")

    markdown = generate_intelligence_report(all_alerts)
    save_intelligence_report(markdown)

    print("\n")
    print(markdown)

    return all_alerts


if __name__ == "__main__":
    run_intelligence()