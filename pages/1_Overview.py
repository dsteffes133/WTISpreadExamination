# ── Relationship Explorer ──────────────────────────────────────────────
import streamlit as st, pandas as pd, plotly.express as px, numpy as np
import statsmodels.api as sm
from src.analytics.term_structure import list_legs    # to gather all columns

# ── Time-series overlay with multi-axis support ────────────────────────
import re, plotly.graph_objects as go
from src.analytics.term_structure import list_legs

# ── Stacked panels overlay ──────────────────────────────────────────────
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# ── time ───────────────────────────────────────────

from datetime import timedelta

st.subheader("📊 Aligned time-series panels")

df: pd.DataFrame = st.session_state["daily_df"].copy()

# ── classify columns ───────────────────────────────────────────────────
leg_cols   = list_legs(df)                                   # outrights
inv_cols   = [c for c in df.columns if "Cushing" in c]       # inventory
spread_cols = [c for c in df.columns                         # spreads
               if c not in leg_cols + inv_cols
               and (" - " in c or c in ["Prompt Spread", "Dec Red"])]

universe = leg_cols + spread_cols + inv_cols

sel = st.multiselect(
    "Pick any series (up to 10)",
    universe,
    default=["%CL 1!", "Prompt Spread", "Cushing Stocks (Mbbl)"],
    max_selections=10,
)

if not sel:
    st.info("Select at least one series."); st.stop()

# ── make working copy & optional anomaly mask ──────────────────────────
df_plot = df[["Date (Day)"] + sel].copy()

min_d = df_plot["Date (Day)"].min().date()
max_d = df_plot["Date (Day)"].max().date()

default_start = max_d - timedelta(days=30)          # last 30 days
if default_start < min_d:
    default_start = min_d                           # edge-case: small dataset

start_d, end_d = st.slider(
    "Date range",
    min_value=min_d,
    max_value=max_d,
    value=(min_d, max_d),                   # ← tuple (start, end)
    format="MMM D YYYY",
)

mask = (
    (df_plot["Date (Day)"] >= pd.Timestamp(start_d)) &
    (df_plot["Date (Day)"] <= pd.Timestamp(end_d))
)
df_plot = df_plot.loc[mask]

if st.checkbox("Hide COVID-era extreme negatives", value=True):
    # mask each chosen outright that fell below $0
    for col in [c for c in sel if c in leg_cols]:
        df_plot.loc[df_plot[col] < 0, col] = np.nan

    # mask chosen spreads whose |value| > $10
    extreme = 10
    for col in [c for c in sel if c in spread_cols]:
        df_plot.loc[df_plot[col].abs() > extreme, col] = np.nan

# ── split selection into panels ────────────────────────────────────────
outs = [c for c in sel if c in leg_cols]
sprs = [c for c in sel if c in spread_cols]
invs = [c for c in sel if c in inv_cols]

rows = [(outs, "Outrights ($/bbl)"),
        (sprs, "Spreads ($/bbl)"),
        (invs, "Inventory (Mbbl)")]
rows = [r for r in rows if r[0]]          # keep non-empty

# ── build stacked figure ───────────────────────────────────────────────
fig = make_subplots(
    rows=len(rows), cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    subplot_titles=[title for _, title in rows],
)

palettes = [
    px.colors.qualitative.Set1,   # first panel colours
    px.colors.qualitative.Set2,   # second panel colours
    px.colors.qualitative.Set3,   # third panel colours
]

row_idx = 1
for grp, _ in rows:
    palette = palettes[row_idx - 1]
    for i, col in enumerate(grp):
        fig.add_trace(
            go.Scatter(
                x=df_plot["Date (Day)"],
                y=df_plot[col],
                mode="lines",
                name=col,
                line=dict(color=palette[i % len(palette)], width=2),
                showlegend=(row_idx == 1),   # one combined legend
            ),
            row=row_idx, col=1,
        )
    row_idx += 1

fig.update_layout(
    height=250 * len(rows) + 100,
    hovermode="x unified",
    legend=dict(orientation="h", y=-0.15),
    margin=dict(l=60, r=40, t=30, b=40),
)

fig.update_traces(fill=None, stackgroup=None)
st.plotly_chart(fig, use_container_width=True)



st.subheader("🔍 Relationship explorer")

# 1) pull DataFrame from session
df: pd.DataFrame = st.session_state["daily_df"]

# 2) build universe of selectable columns (legs + all spreads)
leg_cols    = list_legs(df)
spread_cols = [c for c in df.columns
               if " - " in c or c in ["Prompt Spread", "Dec Red"]]
universe    = leg_cols + spread_cols

# 3) UI — pick X, Y, and return type
col_x = st.selectbox("X-axis series", universe, index=0, key="rel_x")
col_y = st.selectbox("Y-axis series", universe, index=1, key="rel_y")
metric = st.radio(
    "Plot on:",
    ["Price levels", "Daily % change"],
    horizontal=True,
    key="rel_metric"
)

# 4) build plotting DataFrame
if metric == "Price levels":
    plot_df = df[[col_x, col_y]].dropna().copy()
else:
    plot_df = df[[col_x, col_y]].pct_change().dropna().copy()
    plot_df *= 100  # convert to %

# 5) regression for line & stats
X = sm.add_constant(plot_df[col_x])
beta = sm.OLS(plot_df[col_y], X).fit().params[col_x]
corr = np.corrcoef(plot_df[col_x], plot_df[col_y])[0, 1]

# 6) scatter + OLS trendline
fig = px.scatter(
    plot_df,
    x=col_x,
    y=col_y,
    trendline="ols",
    labels={col_x: f"{col_x} ({'% chg' if metric!='Price levels' else '$/bbl'})",
            col_y: f"{col_y} ({'% chg' if metric!='Price levels' else '$/bbl'})"},
)
fig.update_layout(height=500)
fig.update_traces(fill=None, stackgroup=None)

st.plotly_chart(fig, use_container_width=True)
st.caption(
    f"β (slope) = **{beta:.3f}**   |  "
    f"Pearson ρ = **{corr:.2f}**   |  "
    f"Metric = {metric}"
)
