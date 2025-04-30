import streamlit as st, pandas as pd
from src.analytics.term_structure import list_legs
from src.analytics.inv_sensitivity import calc_betas
from src.viz.beta_heatmap import beta_heatmap
from src.viz.beta_table import beta_ranking
from src.viz.beta_scatter import scatter_beta

st.header("📊 Inventory Impact Across the Curve")

# Guard
if "daily_df" not in st.session_state:
    st.warning("⬅️ Upload workbook first."); st.stop()

df: pd.DataFrame = st.session_state["daily_df"].copy()

# ----- 1. Compute betas -------------------------------------------------
legs    = list_legs(df)
spreads = ["Prompt Spread", "Dec Red"]          # add more if you like
beta_df = calc_betas(df, legs, spreads)

# Cache in session for reuse
st.session_state["beta_df"] = beta_df

# ----- 2. Sensitivity Strip (heat-map) ---------------------------------
with st.expander("Heat-map of β vs Δ Cushing"):
    st.plotly_chart(beta_heatmap(beta_df), use_container_width=True)

# ----- 3. Ranking table -------------------------------------------------
with st.expander("Top inventory-sensitive instruments"):
    beta_ranking(beta_df, top=10)

# ----- 4. Scatter drill-down -------------------------------------------
st.subheader("Drill-down scatter")
choice = st.selectbox("Choose instrument", beta_df.index, index=0)
st.plotly_chart(scatter_beta(df, choice), use_container_width=True)
