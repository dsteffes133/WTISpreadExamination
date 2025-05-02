# pages/4_Volatility_Risk.py
import streamlit as st, pandas as pd
from src.analytics.rolling_vol import rolling_vol
from src.viz.vol_panel       import vol_panel
from src.analytics.term_structure import list_legs

# ──────────────────────────  page header  ───────────────────────────
st.header("📉 Volatility & Risk")

# ── workbook guard ──────────────────────────────────────────────────
if "daily_df" not in st.session_state:
    st.warning("⬅️ Upload the Excel workbook on the Home page first.")
    st.stop()

df: pd.DataFrame = st.session_state["daily_df"]

# ── build selectable universe (outrights + spreads) ─────────────────
leg_cols    = list_legs(df)                               # %CL 1! … %CL 12!
spread_cols = [c for c in df.columns
               if " - " in c or c in ["Prompt Spread", "Dec Red",
                                       "Red/Blue", "Blue/Green"]]

universe = leg_cols + spread_cols

# ── UI controls ─────────────────────────────────────────────────────
default_sel = ["%CL 1!", "Prompt Spread", "Dec Red"]
sel_cols = st.multiselect(
    "Choose instruments / spreads (max 8)",
    universe,
    default=default_sel,
    max_selections=8,
)

window = st.slider("Rolling window (days)", 5, 120, 20, step=5)

if not sel_cols:
    st.info("Select at least one series to display.")
    st.stop()

# ── compute rolling σ  ──────────────────────────────────────────────
vol_df = rolling_vol(
    df, sel_cols,
    window=window,
    annualize=True,     # display annualised vols
    min_periods=2       # start after 2 valid returns
)

# ── plot  ────────────────────────────────────────────────────────────
st.plotly_chart(
    vol_panel(vol_df, sel_cols),
    use_container_width=True
)

st.caption(
    f"Volatility = σ(% daily return) rolled **{window} days**, "
    "annualised by √252. Works on outrights *and* any spread."
)

# ── optional debug block (collapse by default) ──────────────────────
with st.expander("🔧 Debug input / σ tail"):
    st.write("**Tail of price inputs**")
    st.write(df[sel_cols].tail(10).T)
    st.write("**Tail of rolling σ**")
    st.write(vol_df[sel_cols].tail(10).T)
