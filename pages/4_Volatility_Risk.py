import streamlit as st, pandas as pd
from src.analytics.rolling_vol import rolling_vol
from src.viz.vol_panel import vol_panel
from src.analytics.term_structure import list_legs   # to auto-gather columns

# ── guard ───────────────────────────────────────────
st.header("📉 Volatility & Risk")

if "daily_df" not in st.session_state:
    st.warning("⬅️ Upload workbook first."); st.stop()

df: pd.DataFrame = st.session_state["daily_df"]

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