# dashboard.py
# Hypersonic Defense Screener — Streamlit Dashboard
# Deployed via Streamlit Cloud
# Accessible from desktop and iPhone

import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime, date

# Add screener folder to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from universe import UNIVERSE
from data import fetch_universe_data
from signals import calculate_universe_signals
from fundamentals import fetch_universe_fundamentals
from score import score_universe
from report import get_universe_posture, generate_signal_groups
from portfolio import build_portfolio_view, identify_gaps
from positions import POSITIONS, CASH, LAST_UPDATED

# --- Page Config ---
st.set_page_config(
page_title="Second Layer Capital",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Custom CSS ---
st.markdown("""
<style>
    .posture-bullish {
        background-color: #1a472a;
        color: #69db7c;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .posture-bearish {
        background-color: #4a1942;
        color: #f783ac;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .posture-mixed {
        background-color: #1c3a5e;
        color: #74c0fc;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .posture-cautious {
        background-color: #3d2a00;
        color: #ffd43b;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .signal-strong {
        color: #69db7c;
        font-weight: bold;
    }
    .signal-neutral {
        color: #74c0fc;
    }
    .signal-weak {
        color: #ffd43b;
        font-weight: bold;
    }
    .signal-critical {
        color: #f783ac;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# --- Data Loading ---
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_all_data():
    """Load all screener data with caching."""
    signals  = calculate_universe_signals(period="6mo")
    scores   = score_universe()
    return signals, scores


def get_posture_html(posture):
    """Return styled posture banner HTML."""
    if "BULLISH" in posture and "CAUTIOUSLY" not in posture:
        css_class = "posture-bullish"
    elif "BEARISH" in posture and "CAUTIOUSLY" not in posture:
        css_class = "posture-bearish"
    elif "CAUTIOUSLY" in posture:
        css_class = "posture-cautious"
    else:
        css_class = "posture-mixed"

    return f'<div class="{css_class}">UNIVERSE POSTURE: {posture}</div>'


# --- Main App ---
def main():
    # Header
    st.title("🛡️ Second Layer Capital")
    st.caption("Hypersonic & Next-Generation Defense | Picks-and-Shovels Strategy")

    # Refresh controls
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.caption(f"Data cached for 1 hour. Last load: {datetime.now().strftime('%B %d, %Y %I:%M %p')}")
    with col2:
        auto_refresh = st.toggle("Auto-refresh (1hr)", value=False)
    with col3:
        refresh = st.button("🔄 Refresh Now", type="primary")

    if refresh:
        st.cache_data.clear()
        st.rerun()

    if auto_refresh:
        import time
        time.sleep(3600)
        st.cache_data.clear()
        st.rerun()

    # Load data
    with st.spinner("Loading screener data..."):
        try:
            signals, scores = load_all_data()
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return

    # --- Universe Posture ---
    posture = get_universe_posture(scores)
    st.markdown(get_posture_html(posture), unsafe_allow_html=True)

    # --- Immediate Observations ---
    st.subheader("📋 Immediate Observations")
    groups = generate_signal_groups(signals)

    observations = []

    if groups["overbought_bullish"]:
        tickers = ", ".join(groups["overbought_bullish"])
        observations.append(
            f"**{tickers}** — Overbought (RSI 70+), Bullish trend. "
            f"Strong momentum but extended — not ideal entry points right now."
        )

    if groups["bullish_volume"]:
        tickers = ", ".join(groups["bullish_volume"])
        observations.append(
            f"**{tickers}** — Bullish trend with volume confirmation. "
            f"Strongest technical setup in the universe today."
        )

    if groups["bullish_neutral"]:
        tickers = ", ".join(groups["bullish_neutral"])
        observations.append(
            f"**{tickers}** — Bullish trend, neutral RSI. "
            f"Cleaner setups — momentum building without being extended."
        )

    if groups["mixed"]:
        tickers = ", ".join(groups["mixed"])
        observations.append(
            f"**{tickers}** — Mixed signals, neither clearly "
            f"bullish nor bearish. No action bias."
        )

    if groups["bearish"]:
        tickers = ", ".join(groups["bearish"])
        observations.append(
            f"**{tickers}** — Bearish trend, trading below key "
            f"moving averages. Warrants caution."
        )

    if groups["oversold"]:
        tickers = ", ".join(groups["oversold"])
        observations.append(
            f"**{tickers}** — Oversold (RSI 30 or below). "
            f"Potential reversal candidate — monitor closely."
        )

    for obs in observations:
        st.markdown(f"- {obs}")

    st.divider()

    # --- Composite Scores ---
    st.subheader("📊 Composite Scores")

    score_data = []
    for s in scores:
        signal_color = {
            "STRONG"  : "🟢",
            "NEUTRAL" : "🔵",
            "WEAK"    : "🟡",
            "CRITICAL": "🔴",
        }.get(s["signal"], "⚪")

        score_data.append({
            "Ticker"      : s["ticker"],
            "Technical"   : s["technical"],
            "Fundamental" : s["fundamental"],
            "Thesis"      : s["thesis"],
            "Score"       : s["composite"],
            "Signal"      : f"{signal_color} {s['signal']}",
            "Action"      : s["action"],
        })

    score_df = pd.DataFrame(score_data)
    score_df.index = range(1, len(score_df) + 1)
    score_df.index.name = "Rank"

    st.dataframe(
        score_df,
        use_container_width=True,
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Score",
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
        }
    )

    st.divider()

    # --- Technical Signals ---
    st.subheader("📈 Technical Signals")

    signal_data = []
    for ticker, s in signals.items():
        signal_data.append({
            "Ticker"     : ticker,
            "Close"      : f"${s['close']:,.2f}",
            "MA20"       : f"${s['ma20']:,.2f}",
            "MA50"       : f"${s['ma50']:,.2f}",
            "RSI"        : s["rsi"],
            "RSI Signal" : s["rsi_signal"],
            "Trend"      : s["trend"],
            "Vol OK"     : "✅" if s["vol_confirmed"] else "❌",
        })

    signal_df = pd.DataFrame(signal_data)
   if not signal_df.empty:
        st.dataframe(signal_df.set_index("Ticker"), use_container_width=True)
    else:
        st.warning("No signal data available — refresh to try again.")

    st.divider()

# --- Portfolio Tracker ---
    st.divider()
    st.subheader("🏈 Active Portfolio — Second Layer Capital (Agentic ••••5038)")

    # Current positions from positions.py
    positions_list = [
        {"ticker": k, "shares": v["shares"], "avg_cost": v["avg_cost"]}
        for k, v in POSITIONS.items()
    ]

    # Show current holdings
    if positions_list:
        st.markdown("**On the Field:**")
        held_tickers = {p["ticker"] for p in positions_list}
        score_lookup  = {s["ticker"]: s for s in scores}

        held_data = []
        for p in positions_list:
            ticker    = p["ticker"]
            s         = score_lookup.get(ticker, {})
            held_data.append({
                "Ticker" : ticker,
                "Shares" : p["shares"],
                "Avg Cost": f"${p['avg_cost']:.2f}",
                "Score"  : s.get("composite", "N/A"),
                "Signal" : s.get("signal", "N/A"),
                "Action" : s.get("action", "N/A"),
            })

        held_df = pd.DataFrame(held_data).set_index("Ticker")
        st.dataframe(held_df, use_container_width=True)
    else:
        st.info("No positions currently held.")

    # Bench players — STRONG signals not held
    gaps = identify_gaps(positions_list, scores)
    if gaps:
        st.markdown("**Bench Players Ready to Come On:**")
        gap_data = []
        for g in gaps:
            gap_data.append({
                "Ticker": g["ticker"],
                "Score" : g["score"],
                "Action": "Consider adding — STRONG signal, not held",
            })
        gap_df = pd.DataFrame(gap_data).set_index("Ticker")
        st.dataframe(gap_df, use_container_width=True)

    st.caption(f"Positions last updated: {LAST_UPDATED} | Cash: ${CASH:.2f}")

    # --- Footer ---
    st.caption(
        f"Hypersonic Defense Screener — {date.today().strftime('%B %d, %Y')} | "
        f"Phase 2 | Technical + Fundamental + Thesis scoring | "
        f"For personal research only — not financial advice."
    )


if __name__ == "__main__":
    main()
