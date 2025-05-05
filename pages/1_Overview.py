# pages/1_Overview.py  – Historical panels (outrights • spreads • inventory)
import streamlit as st, pandas as pd, numpy as np, plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from datetime import timedelta
from src.analytics.term_structure import list_legs

# ── page guard ──────────────────────────────────────────────────────────
st.subheader("📊  Aligned time‑series panels")

if "daily_df" not in st.session_state:
    st.warning("⬅️  Upload workbook first."); st.stop()

df: pd.DataFrame = st.session_state["daily_df"].copy()

# ── classify columns ───────────────────────────────────────────────────
leg_cols    = list_legs(df)                              # outrights
inv_cols    = [c for c in df.columns if "Cushing" in c]  # inventory
spread_cols = [c for c in df.columns                     # spreads
               if c not in leg_cols + inv_cols
               and (" - " in c or c in ["Prompt Spread", "Dec Red"])]

universe = leg_cols + spread_cols + inv_cols

sel = st.multiselect("Pick any series (up to 10)",
                     universe,
                     default=["%CL 1!", "Prompt Spread", "Cushing Stocks (Mbbl) (Release)"],
                     max_selections=10)

if not sel:
    st.info("Select at least one series."); st.stop()

# ── date‑range slider ──────────────────────────────────────────────────
df_plot = df[["Date (Day)"] + sel].copy()

min_d = df_plot["Date (Day)"].min().date()
max_d = df_plot["Date (Day)"].max().date()
default_start = max_d - timedelta(days=30)
if default_start < min_d:
    default_start = min_d

start_d, end_d = st.slider(
    "Date range",
    min_value=min_d, max_value=max_d,
    value=(default_start, max_d),
    format="MMM D YYYY",
)

mask = (
    (df_plot["Date (Day)"] >= pd.Timestamp(start_d)) &
    (df_plot["Date (Day)"] <= pd.Timestamp(end_d))
)
df_plot = df_plot.loc[mask]

# optional data‑sanitiser
if st.checkbox("Hide COVID‑era extreme negatives", value=True):
    for col in [c for c in sel if c in leg_cols]:
        df_plot.loc[df_plot[col] < 0, col] = np.nan
    for col in [c for c in sel if c in spread_cols]:
        df_plot.loc[df_plot[col].abs() > 10, col] = np.nan

# ── split into stacked rows ────────────────────────────────────────────
outs  = [c for c in sel if c in leg_cols]
sprs  = [c for c in sel if c in spread_cols]
invs  = [c for c in sel if c in inv_cols]

rows = [(outs, "Outrights ($/bbl)"),
        (sprs, "Spreads ($/bbl)"),
        (invs, "Inventory (Mbbl)")]
rows = [r for r in rows if r[0]]      # keep non‑empty

# ── build figure ───────────────────────────────────────────────────────
fig = make_subplots(
    rows=len(rows), cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    subplot_titles=[title for _, title in rows],
)

palettes = [px.colors.qualitative.Set1,
            px.colors.qualitative.Set2,
            px.colors.qualitative.Set3]

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
                showlegend=(row_idx == 1)
            ),
            row=row_idx, col=1
        )
    row_idx += 1

fig.update_layout(
    height=250 * len(rows) + 100,
    hovermode="x unified",
    legend=dict(orientation="h", y=-0.15),
    margin=dict(l=60, r=40, t=30, b=40),
)

fig.update_traces(fill="none")     # ensure no area shading
st.plotly_chart(fig, use_container_width=True)
