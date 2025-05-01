# app.py
# ─────────────  Streamlit entry point for the WTI Dashboard  ─────────────
import streamlit as st
from pathlib import Path
from src.preprocessing.daily import load_daily_xlsx
from src.preprocessing.weekly import load_weekly_xlsx

# ── page-wide settings ───────────────────────────────────────────────────
st.set_page_config(
    page_title="WTI Curve Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📈 TI Spreads Dashboard")

# ── file uploader in sidebar ─────────────────────────────────────────────
uploaded = st.sidebar.file_uploader(
    "Upload latest **David WTI Spread Analysis.xlsx**", type="xlsx"
)

# ── caching wrapper so repeated navigation is instant─────────────────────
@st.cache_data(show_spinner="Pre-processing data …", ttl=0)
def _preprocess(xls: Path | str):
    daily_df  = load_daily_xlsx(xls)
    weekly_df = load_weekly_xlsx(xls)
    return daily_df, weekly_df


# ── main logic ───────────────────────────────────────────────────────────
if uploaded:
    daily_df, weekly_df = _preprocess(uploaded)

    # stash in session_state so every page can access without reload
    st.session_state["daily_df"]  = daily_df
    st.session_state["weekly_df"] = weekly_df

    # tiny overview so Home isn’t empty
    st.subheader("Latest snapshot")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Prompt Spread (M1-M2)", f"{daily_df['Prompt Spread'].iloc[-1]:.2f} $/bbl")
        st.metric("Cushing Stocks", f"{daily_df['Cushing Stocks (Mbbl)'].iloc[-1]:,.0f} Mbbl")
    with col2:
        st.metric("Dec Red (Z25-Z26)", f"{daily_df['Dec Red'].iloc[-1]:.2f} $/bbl")
        st.metric("Data through", daily_df["Date (Day)"].iloc[-1].strftime("%d %b %Y"))

    st.success("Data loaded — use the sidebar to navigate pages ➡️")
else:
    st.info(
        "⬅️ **Upload the Excel file** to unlock all dashboard pages."
        "\n\n(Any page you click before uploading will prompt you to come back here.)"
    )
