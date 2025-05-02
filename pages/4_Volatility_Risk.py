import streamlit as st, pandas as pd
from src.analytics.rolling_vol import rolling_vol
from src.viz.vol_panel import vol_panel
from src.analytics.term_structure import list_legs   # to auto-gather columns

# ── guard ───────────────────────────────────────────
st.header("📉 Volatility & Risk")

if "daily_df" not in st.session_state:
    st.warning("⬅️ Upload workbook first."); st.stop()

df: pd.DataFrame = st.session_state["daily_df"]

# add at top of Volatility Risk page, after you load daily_df
target_cols = ["%CL 1!", "%CL 2!", "Prompt Spread"]  # or whichever you're plotting

# show last 25 rows to confirm numeric and NaN pattern
st.write("### Debug: tail of input price columns")
st.write(df[target_cols].tail(25))

# ── build selectable column universe (legs + all spreads) ──────────────
leg_cols     = list_legs(df)
spread_cols  = [c for c in df.columns if " - " in c or c in ["Prompt Spread", "Dec Red"]]
universe     = leg_cols + spread_cols

# ── UI controls ────────────────────────────────────────────────────────
default_sel = ["%CL 1!", "Prompt Spread", "Dec Red"]
sel_cols = st.multiselect(
    "Choose instruments / spreads", universe, default=default_sel, max_selections=8
)

window = st.slider("Rolling window (days)", 5, 120, 20, step=5)

if not sel_cols:
    st.info("Select at least one series."); st.stop()

# ── compute & plot ─────────────────────────────────────────────────────
vol_df = rolling_vol(df, sel_cols, window=window)
st.plotly_chart(vol_panel(vol_df, sel_cols), use_container_width=True)

st.caption(
    f"Volatility computed on % daily returns, rolled {window} days "
    "(annualised). Works on outrights *and* any spread."
)

vol_debug = rolling_vol(df, ["%CL 1!"], window=20,
                        annualize=False, min_periods=2, gap_ffill=3)

st.write("### Debug: rolling_vol tail")
st.write(vol_debug.tail(25))