# universe.py
# Defines the investable universe for the Hypersonic Defense Screener
# All tickers and metadata sourced from UNIVERSE.md
# Update this file whenever UNIVERSE.md is updated

UNIVERSE = {
    # AI & Autonomy
    "PLTR": {"name": "Palantir Technologies",    "domain": "AI & Autonomy",                          "sector": "AI & Autonomy"},
    "AVAV": {"name": "AeroVironment",             "domain": "Tactical loitering munitions & small UAS","sector": "AI & Autonomy"},
    "KTOS": {"name": "Kratos Defense",            "domain": "Autonomous jet platforms & target testbeds","sector": "AI & Autonomy / Hypersonic"},

    # Hypersonic, Space & Propulsion Infrastructure
    "KRMN": {"name": "Karman Holdings",           "domain": "Payload protection & interstage structures","sector": "Hypersonic, Space & Propulsion"},
    "HWM":  {"name": "Howmet Aerospace",          "domain": "Refractory alloys & thermal protection", "sector": "Hypersonic, Space & Propulsion"},
    "ATI":  {"name": "ATI Inc",                   "domain": "Titanium alloys & high-speed airframes",  "sector": "Hypersonic, Space & Propulsion"},

    # IoMT, Sensors & Digital Battlefield
    "AXON": {"name": "Axon Enterprise",           "domain": "Tactical sensors, software nodes, drone orchestration","sector": "IoMT & Digital Battlefield"},
    "TDY":  {"name": "Teledyne Technologies",     "domain": "Defense electronics & harsh-environment imaging","sector": "IoMT & Digital Battlefield"},
    "HEI":  {"name": "Heico Corporation",         "domain": "Proprietary subcomponents & defense electronics","sector": "IoMT & Digital Battlefield"},
    "LOAR": {"name": "Loar Holdings",             "domain": "High-margin precision aerospace subcomponents","sector": "IoMT & Digital Battlefield"},

    # Industrial Supply Chain & Materials
    "MTRN": {"name": "Materion",                  "domain": "Specialty beryllium alloys & optical/guidance subcomponents","sector": "Industrial Supply Chain"},
    "CW":   {"name": "Curtiss-Wright Corporation", "domain": "Defense electronics, naval systems, motion control",        "sector": "IoMT & Digital Battlefield"},}

# Watchlist - under research, not yet scored
WATCHLIST = {
    "FLY":  {"name": "Firefly Aerospace",         "domain": "Responsive space launch & tactical transit"},
    "AADX": {"name": "Applied Aerospace & Defense","domain": "Solid rocket motors & missile propulsion"},
    "BAH":  {"name": "Booz Allen Hamilton",       "domain": "Defense services & AI deployment integration"},
}

if __name__ == "__main__":
    print(f"Universe: {len(UNIVERSE)} tickers")
    print(f"Watchlist: {len(WATCHLIST)} tickers")
    for ticker, meta in UNIVERSE.items():
        print(f"  {ticker:<6} — {meta['name']:<35} [{meta['sector']}]")