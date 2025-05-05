import streamlit as st, pandas as pd
from src.analytics.nn_features import build_feature_matrix
from src.analytics.nn_search   import knn_search
from src.analytics.nn_forward  import forward_outcomes
from src.viz.nn_report         import neighbour_table, outcome_bar

st.header("🔍  Historical Analogue Finder")

if "daily_df" not in st.session_state:
    st.warning("⬅️ Upload workbook first."); st.stop()

df: pd.DataFrame = st.session_state["daily_df"]

# build + cache feature matrix
@st.cache_data
def _features(df):
    return build_feature_matrix(df)
X, meta = _features(df)

# UI
query = st.date_input("Query date", X.index[-1].date(),
                      min_value=X.index[0].date(),
                      max_value=X.index[-1].date())
k   = st.slider("Neighbours (k)", 3, 15, 5)
fwd = st.slider("Forward days", 5, 30, 10, step=5)

spread_choices = ["Prompt Spread", "Dec Red"] +  \
                 [c for c in df.columns if " - " in c][:5]
targets = st.multiselect("Target spreads", spread_choices, default=["Prompt Spread"])

# run
nbrs = knn_search(X, pd.Timestamp(query), k)
st.subheader("Nearest neighbours")
st.dataframe(neighbour_table(meta.loc[nbrs.index], nbrs["Distance"]))

out = forward_outcomes(df, nbrs.index, targets, fwd_days=fwd)
mean_ret = out.mean().sort_values(key=abs, ascending=False)

st.subheader(f"Avg Δ over {fwd} days (across neighbours)")
st.plotly_chart(outcome_bar(mean_ret), use_container_width=True)
