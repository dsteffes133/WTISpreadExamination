# pages/5_Historical_Analogues.py
# ---------------------------------------------------------------
# Interactive nearest‑neighbour analogue finder
# ---------------------------------------------------------------
import streamlit as st, pandas as pd
from src.analytics.nn_features  import build_feature_matrix
from src.analytics.nn_search    import knn_search
from src.analytics.nn_forward   import forward_outcomes
from src.viz.nn_report          import neighbour_table, outcome_bar

st.header("🔍  Historical Analogue Finder")

# ── guard ───────────────────────────────────────────────────────
if "daily_df" not in st.session_state:
    st.warning("⬅️  Upload workbook first."); st.stop()

# tidy DataFrame (index = date)
df: pd.DataFrame = st.session_state["daily_df"].copy()
df["Date (Day)"] = pd.to_datetime(df["Date (Day)"])
df = df.set_index("Date (Day)").sort_index()

# ── feature‑set selector (Full / Limited) ───────────────────────
mode_label = st.selectbox(
    "Feature set",
    [
        "Full  –  curve slopes, z‑scores, ΔCushing, etc.",
        "Limited – outrights 1‑12, Prompt, Dec Red, CL2‑CL8, Cushing"
    ],
    index=0
)
mode_key = "limited" if mode_label.startswith("Limited") else "full"

# ---- build & cache feature matrix ------------------------------
@st.cache_data(show_spinner="Building feature matrix …")
def _features(dframe, mode):
    return build_feature_matrix(dframe, mode=mode)

X, meta = _features(df, mode_key)

# ── UI controls -------------------------------------------------
query = st.date_input(
    "Query date",
    X.index[-1].date(),
    min_value=X.index[0].date(),
    max_value=X.index[-1].date(),
)

k     = st.slider("Neighbours (k)",               3, 15, 5)
fwd   = st.slider("Forward days",                 5, 30, 10, step=5)
gap   = st.slider("Black‑out window ± days",      5, 90, 30, step=5)

spread_choices = (
    ["Prompt Spread", "Dec Red"] +
    [c for c in df.columns if " - " in c][:5]        # first 5 spreads
)
targets = st.multiselect("Target spreads", spread_choices,
                         default=["Prompt Spread"])

# ── nearest‑neighbour search -----------------------------------
try:
    nbrs = knn_search(
        X,
        pd.Timestamp(query),
        k=k,
        min_gap=gap,        # exclude dates within ±gap of query
        dedup_gap=7         # neighbours themselves ≥7 d apart
    )
except ValueError as err:
    st.error(str(err)); st.stop()

# ── neighbour table --------------------------------------------
st.subheader("Nearest neighbours")
st.dataframe(
    neighbour_table(meta.loc[nbrs.index], nbrs["Distance"]),
    use_container_width=True
)

# ── forward outcome analysis -----------------------------------
out = forward_outcomes(df, nbrs.index, targets, fwd_days=fwd)
mean_ret = out.mean().sort_values(key=abs, ascending=False)

st.subheader(f"Average Δ over {fwd} days (across neighbours)")
st.plotly_chart(outcome_bar(mean_ret), use_container_width=True)

if targets:
    tgt = targets[0]                     # plot just the first target
    ts = df[tgt].dropna()

    import plotly.graph_objects as go
    fig_hist = go.Figure()

    # full history line
    fig_hist.add_trace(go.Scatter(
        x=ts.index, y=ts.values,
        mode="lines",
        name=tgt,
        line=dict(color="royalblue")
    ))

    # add semi‑transparent vrect for ±7 day window of each neighbour
    for dt in nbrs.index:
        start = dt - pd.Timedelta(days=7)
        end   = dt + pd.Timedelta(days=7)
        fig_hist.add_vrect(
            x0=start, x1=end,
            fillcolor="orange", opacity=0.25, layer="below", line_width=0
        )
        # marker on the exact neighbour date
        fig_hist.add_trace(go.Scatter(
            x=[dt], y=[ts.loc[dt]],
            mode="markers", marker=dict(color="red", size=6),
            showlegend=False
        ))

    fig_hist.update_layout(
        title=f"{tgt} — full history  (orange = ±7 d around neighbours)",
        height=400,
        margin=dict(l=60, r=40, t=50, b=40),
        hovermode="x unified"
    )
    fig_hist.update_traces(fill="none")
    st.plotly_chart(fig_hist, use_container_width=True)

    # ── neighbour Δ table (numeric, no chart) --------------------------
    delta_tbl = out[[tgt]].rename(columns={tgt: f"Δ{fwd}d"})
    st.subheader(f"{tgt} — forward Δ over {fwd} days")
    st.dataframe(
        delta_tbl.style.format("{:+.2f}"),
        use_container_width=True,
        hide_index=False,
    )
else:
    st.info("Select at least one target spread to show history plot.")

# ── caption -----------------------------------------------------
st.caption(
    f"**Feature mode**: {mode_label.split('–')[0].strip()}  •  "
    f"Query = {query}  •  "
    f"Neighbours = {k}, blackout ±{gap} d, de‑dup ≥7 d."
)
