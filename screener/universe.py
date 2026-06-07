# universe.py
# Defines the investable universe for the Hypersonic Defense Screener
# All tickers and metadata sourced from UNIVERSE.md
# Update this file whenever UNIVERSE.md is updated

UNIVERSE = {
    "ATI":  {"name": "ATI Inc",                  "domain": "Advanced materials, titanium alloys"},
    "AVAV": {"name": "AeroVironment",             "domain": "Autonomous systems, loitering munitions"},
    "HEI":  {"name": "Heico Corporation",         "domain": "Aerospace/defense components"},
    "HWM":  {"name": "Howmet Aerospace",          "domain": "Advanced materials, precision castings"},
    "KRMN": {"name": "Karman Holdings",           "domain": "Propulsion, payload protection, composites"},
    "KTOS": {"name": "Kratos Defense",            "domain": "Hypersonic test platforms, autonomous systems"},
    "LOAR": {"name": "Loar Holdings",             "domain": "Precision aerospace/defense components"},
    "MTRN": {"name": "Materion",                  "domain": "Specialty alloys, advanced materials"},
    "SXI":  {"name": "Standex International",     "domain": "Electronics, sensors, aerospace/defense"},
    "TDY":  {"name": "Teledyne Technologies",     "domain": "Defense electronics, optical components"},
    "VELO": {"name": "Velo3D",                    "domain": "Additive manufacturing"},
}

# Watchlist - under research, not yet scored
WATCHLIST = {
    "BWX":  {"name": "BWX Technologies",          "domain": "Nuclear propulsion, naval platforms"},
    "MRCY": {"name": "Mercury Systems",           "domain": "Defense electronics, hypersonic guidance"},
    "AIRO": {"name": "AIRO Group Holdings",       "domain": "Emerging defense aerospace"},
}

if __name__ == "__main__":
    print(f"Universe: {len(UNIVERSE)} tickers")
    print(f"Watchlist: {len(WATCHLIST)} tickers")
    for ticker, meta in UNIVERSE.items():
        print(f"  {ticker:<6} — {meta['name']}")
        