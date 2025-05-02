# ──────────────────────────  app.py  ────────────────────────────
# Streamlit entry point for the WTI Curve / Spread dashboard
import streamlit as st
from pathlib import Path
from src.preprocessing.daily import load_daily_xlsx

# ── Page-wide settings ──────────────────────────────────────────
st.set_page_config(
    page_title="WTI Curve Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📈 WTI Curve & Spread Dashboard")

# ── Excel uploader ──────────────────────────────────────────────
uploaded = st.sidebar.file_uploader(
    "Upload **David WTI Spread Analysis.xlsx**", type="xlsx"
)

# ── Cache pre-processing so navigation is instant ──────────────
@st.cache_data(show_spinner="Pre-processing workbook …", ttl=0)
def _preprocess(xls: Path | str):
    """Return fully-engineered daily_df (weekly data folded in)."""
    return load_daily_xlsx(xls)


# ── Main logic ──────────────────────────────────────────────────
if uploaded:
    daily_df = _preprocess(uploaded)

    # store once for all sub-pages
    st.session_state["daily_df"] = daily_df

    # ── Mini dashboard so Home isn’t empty ──────────────────────
    st.subheader("Latest snapshot")

    # guard for optional columns
    def safe_metric(colname, fmt="{:.2f}", fallback="—"):
        try:
            val = daily_df[colname].iloc[-1]
            return fmt.format(val)
        except KeyError:
            return fallback

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Prompt Spread (M1–M2)",
              safe_metric("Prompt Spread", "{:.2f} $/bbl"))

    c2.metric("Dec Red (Z → Z+1)",
              safe_metric("Dec Red", "{:.2f} $/bbl"))

    c3.metric("Cushing Stocks",
              safe_metric("Cushing Stocks (Mbbl)",
                          "{:,.0f} Mbbl"))

    latest_date = daily_df["Date (Day)"].iloc[-1]
    c4.metric("Data through", latest_date.strftime("%d %b %Y"))

    st.success("Workbook loaded ✔︎ — use the sidebar to explore pages ➡️")

else:
    st.info(
        "⬅️ **Upload the latest Excel file** to unlock the dashboard."
        "\n\n(Clicking any other page before upload will redirect you back here.)"
    )
