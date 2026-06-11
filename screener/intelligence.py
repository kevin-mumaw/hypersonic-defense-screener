# intelligence.py
# Monitors public data sources for thesis-relevant events
# Sources: Defense.gov RSS, Congress.gov API, SEC EDGAR
# Output: Alert flags for manual review — nothing changes automatically
# Human review required before any thesis score override

import requests
import xml.etree.ElementTree as ET
from datetime import date, datetime
import os
import sys
import time
import json
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from universe import UNIVERSE

# --- Configuration ---

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

# Exact company names for SEC EDGAR — must match filing company name
IPO_WATCHLIST = {
    "Anduril Industries": ["Anduril Industries", "Anduril"],
    "Shield AI":          ["ShieldAI", "Shield AI Inc"],
}

MIN_CONTRACT_VALUE = 50_000_000
CURRENT_YEAR = date.today().year


# --- Pentagon Contract RSS Feed ---

def scrape_pentagon_contracts():
    """
    Pull Defense.gov contract announcements via RSS feed.
    Flags any mention of universe companies.
    """
    alerts = []
    
    # Defense.gov RSS feeds
    rss_urls = [
        "https://www.defense.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=945&max=20",
        "https://www.defense.gov/News/Contracts/rss/",
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; research/1.0)"
    }

    fetched = False
    for url in rss_urls:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            items = root.findall(".//item")
            
            if not items:
                continue
                
            fetched = True
            
            for item in items[:30]:
                title       = item.findtext("title", "")
                description = item.findtext("description", "")
                link        = item.findtext("link", "")
                pub_date    = item.findtext("pubDate", "")
                
                full_text = f"{title} {description}".lower()
                
                for ticker, names in COMPANY_NAMES.items():
                    for name in names:
                        if name.lower() in full_text:
                            alerts.append({
                                "source"  : "Pentagon Contracts (RSS)",
                                "ticker"  : ticker,
                                "company" : names[0],
                                "title"   : title,
                                "text"    : description[:300],
                                "url"     : link,
                                "date"    : pub_date,
                                "action"  : f"Review thesis score override for {ticker} (currently {get_current_thesis_score(ticker)})",
                            })
                            break
            break
            
        except Exception as e:
            continue
    
    if not fetched:
        alerts.append({
            "source"  : "Pentagon Contracts (RSS)",
            "ticker"  : "ERROR",
            "company" : "N/A",
            "text"    : "RSS feed unavailable — check defense.gov manually",
            "url"     : "https://www.defense.gov/News/Contracts/",
            "date"    : "",
            "action"  : "Manual check required",
        })
    
    return alerts


# --- Congress.gov NDAA Monitor ---

def scrape_ndaa_keywords():
    """
    Monitor Congress.gov for NDAA legislation containing
    thesis-relevant keywords via public search API.
    """
    alerts = []
    
    # Congress.gov public search — no API key required for basic search
    base_url = "https://api.congress.gov/v3/bill"
    api_key = os.getenv("CONGRESS_API_KEY", "")

    # Search for recent NDAA bills
    params = {
        "query"  : "national defense authorization",
        "sort"   : "updateDate+desc",
        "limit"  : 5,
        "format" : "json",
        "api_key": api_key,
    }
    
    headers = {
        "User-Agent": "hypersonic-defense-screener/1.0"
    }
    
    try:
        response = requests.get(base_url, params=params, 
                               headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        bills = data.get("bills", [])
        
        for bill in bills:
            title   = bill.get("title", "")
            number  = bill.get("number", "")
            congress= bill.get("congress", "")
            url     = bill.get("url", "")
            
            full_text = title.lower()
            
            for keyword in NDAA_KEYWORDS:
                if keyword.lower() in full_text:
                    alerts.append({
                        "source"  : "Congress.gov NDAA",
                        "ticker"  : "UNIVERSE",
                        "keyword" : keyword,
                        "title"   : title,
                        "text"    : f"Bill {number}, Congress {congress}: {title}",
                        "url"     : url,
                        "action"  : f"Review NDAA language re: '{keyword}' — may affect thesis weighting",
                    })
                    break
                    
    except Exception as e:
        # Fallback — try simple web search for recent NDAA news
        alerts.append({
            "source"  : "Congress.gov NDAA",
            "ticker"  : "INFO",
            "keyword" : "N/A",
            "title"   : "API unavailable",
            "text"    : f"Congress.gov API error: {str(e)} — monitor manually",
            "url"     : "https://www.congress.gov",
            "action"  : "Check congress.gov for recent NDAA updates manually",
        })
    
    return alerts


# --- SEC EDGAR IPO Watchlist ---

def scrape_sec_ipo_watchlist():
    """
    Monitor SEC EDGAR for S-1 filings from IPO watchlist.
    Uses exact company name matching to avoid false positives.
    Filters to current year only.
    """
    alerts = []
    current_year_str = str(CURRENT_YEAR)

    for company, exact_names in IPO_WATCHLIST.items():
        found = False
        
        for exact_name in exact_names:
            # Use EDGAR full-text search API
            url = "https://efts.sec.gov/LATEST/search-index"
            params = {
                "q"    : f'"{exact_name}"',
                "forms": "S-1,S-1/A",
                "hits.hits.total.value": 5,
            }
            headers = {
                "User-Agent": "hypersonic-defense-screener research@example.com"
            }
            try:
                response = requests.get(url, params=params,
                                       headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                hits = data.get("hits", {}).get("hits", [])
                
                # Filter for exact company name matches only
                for hit in hits[:5]:
                    source      = hit.get("_source", {})
                    entity_name = source.get("entity_name", "")
                    file_date   = source.get("file_date", "")
                    
                    # Strict match — entity name must contain 
                    # exact company name
                    if (exact_name.lower() in entity_name.lower()
                            and file_date.startswith(current_year_str)):
                        alerts.append({
                            "source"  : "SEC EDGAR S-1 Watch",
                            "ticker"  : "🚨 IPO ALERT",
                            "company" : company,
                            "text"    : f"S-1 filed {file_date} by {entity_name}",
                            "url"     : f"https://www.sec.gov/cgi-bin/browse-edgar?company={exact_name.replace(' ', '+')}&action=getcompany&type=S-1",
                            "action"  : f"IMMEDIATE: {company} S-1 detected — prepare to add to universe on IPO date",
                        })
                        found = True
                        break
                        
                if found:
                    break
                    
            except Exception as e:
                alerts.append({
                    "source"  : "SEC EDGAR S-1 Watch",
                    "ticker"  : "ERROR",
                    "company" : company,
                    "text"    : f"EDGAR error: {str(e)}",
                    "url"     : "https://efts.sec.gov",
                    "action"  : f"Check SEC EDGAR manually for {company}",
                })
                break
            
            time.sleep(0.5)
        
        # If no filing found — confirm still private
        if not found and not any(
            a["ticker"] == "ERROR" and a["company"] == company 
            for a in alerts
        ):
            alerts.append({
                "source"  : "SEC EDGAR S-1 Watch",
                "ticker"  : "✅ Still Private",
                "company" : company,
                "text"    : f"No {current_year_str} S-1 filing detected for {company}",
                "url"     : "https://efts.sec.gov",
                "action"  : "No action required — continue monitoring",
            })

    return alerts


# --- Helper ---

def get_current_thesis_score(ticker):
    """Get current thesis score override for a ticker."""
    THESIS_OVERRIDES = {
        "KRMN": 85, "KTOS": 80, "AVAV": 75, "TDY": 75,
        "HWM": 70,  "ATI": 70,  "LOAR": 65, "HEI": 65,
        "MTRN": 65, "SXI": 45,  "VELO": 40, "PLTR": 85,
        "AXON": 75,
    }
    return THESIS_OVERRIDES.get(ticker, "N/A")


# --- Report Generator ---

def generate_intelligence_report(all_alerts):
    """Generate markdown intelligence report."""
    today = date.today().strftime("%B %d, %Y")
    lines = []

    lines.append("# Hypersonic Defense Screener — Intelligence Report")
    lines.append(f"## {today}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("> **Manual review required for all alerts.**")
    lines.append("> Nothing changes automatically.")
    lines.append("> Update thesis score overrides in `score.py` manually.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Pentagon
    lines.append("## Pentagon Contract Alerts")
    lines.append("")
    contract_alerts = [a for a in all_alerts
                      if a["source"] == "Pentagon Contracts (RSS)"
                      and a["ticker"] != "ERROR"]
    contract_errors = [a for a in all_alerts
                      if a["source"] == "Pentagon Contracts (RSS)"
                      and a["ticker"] == "ERROR"]

    if contract_alerts:
        for a in contract_alerts:
            lines.append(f"### 🚨 {a['ticker']} — {a['company']}")
            lines.append(f"**Date:** {a.get('date', 'Unknown')}")
            lines.append(f"**Title:** {a['title']}")
            lines.append(f"**Detail:** {a['text']}")
            lines.append(f"**Source:** {a['url']}")
            lines.append(f"**Action:** {a['action']}")
            lines.append("")
    elif contract_errors:
        lines.append(f"> ⚠️ {contract_errors[0]['text']}")
        lines.append(f"> Manual check: {contract_errors[0]['url']}")
        lines.append("")
    else:
        lines.append("> No universe companies in recent contracts.")
        lines.append("")

    lines.append("---")
    lines.append("")

    # NDAA
    lines.append("## NDAA Keyword Alerts")
    lines.append("")
    ndaa_alerts = [a for a in all_alerts
                  if a["source"] == "Congress.gov NDAA"
                  and a["ticker"] not in ("ERROR", "INFO")]
    ndaa_info   = [a for a in all_alerts
                  if a["source"] == "Congress.gov NDAA"
                  and a["ticker"] == "INFO"]

    if ndaa_alerts:
        for a in ndaa_alerts:
            lines.append(f"### 📋 Keyword: '{a['keyword']}'")
            lines.append(f"**Bill:** {a['text']}")
            lines.append(f"**Source:** {a['url']}")
            lines.append(f"**Action:** {a['action']}")
            lines.append("")
    elif ndaa_info:
        lines.append(f"> ℹ️ {ndaa_info[0]['text']}")
        lines.append(f"> Manual check: {ndaa_info[0]['url']}")
        lines.append("")
    else:
        lines.append("> No new NDAA keyword matches found.")
        lines.append("")

    lines.append("---")
    lines.append("")

    # SEC EDGAR
    lines.append("## SEC EDGAR IPO Watch")
    lines.append("")
    sec_alerts  = [a for a in all_alerts
                  if a["source"] == "SEC EDGAR S-1 Watch"
                  and "ALERT" in a["ticker"]]
    sec_status  = [a for a in all_alerts
                  if a["source"] == "SEC EDGAR S-1 Watch"
                  and "Private" in a["ticker"]]
    sec_errors  = [a for a in all_alerts
                  if a["source"] == "SEC EDGAR S-1 Watch"
                  and a["ticker"] == "ERROR"]

    if sec_alerts:
        for a in sec_alerts:
            lines.append(f"### 🔔 {a['ticker']} — {a['company']}")
            lines.append(f"**Filing:** {a['text']}")
            lines.append(f"**Source:** {a['url']}")
            lines.append(f"**Action:** {a['action']}")
            lines.append("")
    
    for a in sec_status:
        lines.append(f"- {a['ticker']} **{a['company']}** — {a['text']}")
    
    if sec_errors:
        for a in sec_errors:
            lines.append(f"> ⚠️ {a['text']} ({a['company']})")
    
    if not sec_alerts and not sec_status and not sec_errors:
        lines.append("> SEC EDGAR check produced no results.")
    
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
    """Run all intelligence scrapers and generate report."""
    print("Running intelligence scrapers...")
    print("(Manual review required for all alerts)\n")

    all_alerts = []

    print("Checking Pentagon contracts (RSS)...")
    all_alerts.extend(scrape_pentagon_contracts())
    time.sleep(1)

    print("Checking Congress.gov NDAA...")
    all_alerts.extend(scrape_ndaa_keywords())
    time.sleep(1)

    print("Checking SEC EDGAR IPO watchlist...")
    all_alerts.extend(scrape_sec_ipo_watchlist())

    action_alerts = [a for a in all_alerts 
                    if a["ticker"] not in ("ERROR", "INFO", "✅ Still Private")]
    print(f"\nAction alerts: {len(action_alerts)}")

    markdown = generate_intelligence_report(all_alerts)
    save_intelligence_report(markdown)

    print("\n")
    print(markdown)

    return all_alerts


if __name__ == "__main__":
    run_intelligence()