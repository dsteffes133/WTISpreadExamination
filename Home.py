# Home.py  –  dashboard landing page
import streamlit as st, pandas as pd
from pathlib import Path
from src.preprocessing.daily import load_daily_xlsx

# page config
st.set_page_config(
    page_title="WTI Curve Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("📈 WTI Curve & Spread Dashboard")

# uploader
uploaded = st.sidebar.file_uploader(
    "Upload **David WTI Spread Analysis.xlsx**", type="xlsx"
)

# cache
@st.cache_data(show_spinner="Pre‑processing workbook …", ttl=0)
def _preprocess(path: Path | str) -> pd.DataFrame:
    return load_daily_xlsx(path)

# main
if uploaded:
    daily_df = _preprocess(uploaded)
    st.session_state["daily_df"] = daily_df

    # helper shows first non‑NaN among candidate columns
    def metric_val(cols, fmt="{:.2f}", fallback="—"):
        for c in cols:
            if c in daily_df.columns and pd.notna(daily_df[c].iloc[-1]):
                return fmt.format(daily_df[c].iloc[-1])
        return fallback

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prompt Spread (M1–M2)",
              metric_val(["Prompt Spread",
                          "%CL 1! - %CL 2!"],
                         "{:.2f} $/bbl"))

    c2.metric("Dec Red (Z → Z+1)",
              metric_val(["Dec Red"], "{:.2f} $/bbl"))

    c3.metric("Cushing Stocks",
              metric_val(["Cushing Stocks (Interp)",
                          "Cushing Stocks (Mbbl)",
                          "Cushing Stocks (Mbbl) (Release)"],
                         "{:,.0f} Mbbl"))

    last_date = pd.to_datetime(daily_df["Date (Day)"].iloc[-1])
    c4.metric("Data through", last_date.strftime("%d %b %Y"))

    st.success("Workbook loaded ✔︎ — use the sidebar to explore pages ➡️")

else:
    st.info(
        "⬅️ Upload the latest workbook to unlock the dashboard."
        "\n\n(Any page clicked before upload will redirect you back.)"
    )

with st.expander("🔧 Debug last row"):
    st.write(daily_df.tail(3))  # show last 3 dates, 15 cols
