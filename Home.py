# ─────────────────────────────  Home.py  ─────────────────────────────
# Landing page for the WTI Curve & Spread dashboard
import streamlit as st, pandas as pd
from io import BytesIO
from src.preprocessing.daily import load_daily_xlsx

# ──  page config  ────────────────────────────────────────────────────
st.set_page_config(
    page_title="WTI Curve Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("📈 WTI Curve & Spread Dashboard")

# ──  file‑uploader (sidebar)  ────────────────────────────────────────
uploaded = st.sidebar.file_uploader(
    "Upload **David WTI Spread Analysis.xlsx**", type="xlsx"
)

# ──  persist raw bytes so a script error won’t drop the file  ───────
if uploaded is not None:
    st.session_state["xls_bytes"] = uploaded.getvalue()      # overwrite only on new upload

# ──  cached pre‑processing (keyed by bytes)  ─────────────────────────
@st.cache_data(show_spinner="Pre‑processing workbook …", ttl=0)
def _preprocess(raw_bytes: bytes) -> pd.DataFrame:
    return load_daily_xlsx(BytesIO(raw_bytes))

# ──  load DataFrame if we have bytes  ────────────────────────────────
if "xls_bytes" in st.session_state:
    daily_df = _preprocess(st.session_state["xls_bytes"])
    st.session_state["daily_df"] = daily_df
else:
    daily_df = None

# ──  Snapshot metrics  ───────────────────────────────────────────────
if daily_df is not None:

    # helper: first non‑NaN among candidate columns
    def metric_val(cols, fmt="{:.2f}", fallback="—"):
        for c in cols:
            if c in daily_df.columns and pd.notna(daily_df[c].iloc[-1]):
                return fmt.format(daily_df[c].iloc[-1])
        return fallback

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Prompt Spread (M1–M2)",
              metric_val(["Prompt Spread", "%CL 1! - %CL 2!"],
                         "{:.2f} $/bbl"))

    c2.metric("Dec Red (Z → Z+1)",
              metric_val(["Dec Red"], "{:.2f} $/bbl"))

    c3.metric("Cushing Stocks",
              metric_val(["Cushing Stocks (Interp)",
                          "Cushing Stocks (Mbbl)",
                          "Cushing Stocks (Mbbl) (Release)"],
                         "{:,.0f} Mbbl"))

    last_date = pd.to_datetime(daily_df["Date (Day)"].dropna().iloc[-1])
    c4.metric("Data through", last_date.strftime("%d %b %Y"))

    st.success("Workbook loaded ✔︎ — use the sidebar to explore pages ➡️")


else:
    st.info(
        "⬅️ Upload the latest workbook to unlock the dashboard."
        "\n\n(Once uploaded, the file persists in the session even if a page errors.)"
    )
