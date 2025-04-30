# pages/2_Curve_Spreads.py
import streamlit as st
import pandas as pd
from datetime import date as date_cls
from src.viz.curve import make_curve_figure
from src.analytics.term_structure import list_legs
from src.analytics.top_movers import top_movers
from src.viz.leaderboard import show_leaderboard
from src.viz.waterfall import waterfall_curve

st.header("Forward Curve & Spread Ladder")

daily_df: pd.DataFrame = st.session_state["daily_df"]

# ── date slider ─────────────────────────────────────────────────────────
min_d, max_d = daily_df["Date (Day)"].min(), daily_df["Date (Day)"].max()
picked = st.slider(
    "Pick a date",
    min_value=min_d.date(),
    max_value=max_d.date(),
    value=max_d.date(),
    format="MMM D YYYY"
)
picked_ts = pd.Timestamp(picked)

# ── forward-curve strip ────────────────────────────────────────────────
fig_curve = make_curve_figure(daily_df.set_index("Date (Day)"), picked_ts)
st.plotly_chart(fig_curve, use_container_width=True)

st.caption("Green segments = backwardation (near > far), Red = contango.")


st.subheader("⚡ Top curve movers (60-day z-score)")
leader = top_movers(daily_df, window=60, k=7)
show_leaderboard(leader)




st.subheader("Overnight curve change")

# a) get an ordered list of available dates
dates = pd.to_datetime(daily_df["Date (Day)"]).sort_values().unique()

# b) Streamlit date-slider (skip the very first row since we need t-1)
picked_date = st.slider(
    "Select day",
    min_value=dates[1].to_pydatetime(),          # earliest allowed
    max_value=dates[-1].to_pydatetime(),         # latest (today)
    value=dates[-1].to_pydatetime(),             # default = latest
    format="MMM D YYYY"
)

# c) convert the chosen date back to row index
idx = daily_df.index[daily_df["Date (Day)"] == pd.Timestamp(picked_date)][0]

# d) build the chart (idx is position not label)
wf_fig = waterfall_curve(daily_df.reset_index(drop=True), idx, threshold=0.20)
st.plotly_chart(wf_fig, use_container_width=True)
st.caption("Segments coloured when |Δ| > 0.20 $/bbl overnight.")