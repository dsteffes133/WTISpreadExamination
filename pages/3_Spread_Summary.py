import streamlit as st, pandas as pd, plotly.graph_objects as go, plotly.express as px
from datetime import timedelta
from src.analytics.term_structure import list_legs
from src.analytics.spread_summary import compute_spread, summary_stats

st.header("📊 Spread Summary & Analysis")

# ── Guard ─────────────────────────────────────────────────────────────
if "daily_df" not in st.session_state:
    st.warning("Upload workbook first."); st.stop()

df: pd.DataFrame = st.session_state["daily_df"]

# ── 1. Choose legs & date window ──────────────────────────────────────
legs = list_legs(df)

# quick presets
presets = {
    "Prompt Spread (M1-M2)": ("%CL 1!", "%CL 2!"),
    "Dec Red (Z25-Z26)":     ("CL Z25", "CL Z26"),
}

preset = st.selectbox("Quick spread", ["<Custom>"] + list(presets.keys()))
if preset != "<Custom>":
    near, far = presets[preset]      # auto-fill selectors
    col1, col2 = st.columns(2)
    near = col1.selectbox("Near leg", legs, index=legs.index(near))
    far  = col2.selectbox("Far  leg",  legs, index=legs.index(far))
else:
    col1, col2 = st.columns(2)
    near = col1.selectbox("Near leg", legs, index=0)
    far  = col2.selectbox("Far  leg",  legs, index=1)


spread_name = f"{near} - {far}"
df["Spread"] = compute_spread(df, near, far)

# date-range slider
min_d = df["Date (Day)"].min().date()
max_d = df["Date (Day)"].max().date()
default_start = max_d - timedelta(days=365)

start_d, end_d = st.slider(
    "Date range",
    min_value=min_d,
    max_value=max_d,
    value=(min_d, max_d),
    format="MMM D YYYY"
)

mask = (df["Date (Day)"] >= pd.Timestamp(start_d)) & (df["Date (Day)"] <= pd.Timestamp(end_d))
dff = df.loc[mask].copy()

spread = dff.set_index("Date (Day)")["Spread"]

# ── COVID window toggle ───────────────────────────────────────────────
covid_start = pd.Timestamp("2020-04-01")
covid_end   = pd.Timestamp("2020-05-15")

hide_covid = st.checkbox(
    "Hide COVID negative-oil shock (Apr-May 2020)",
    value=True
)

if hide_covid:
    dff = dff[~((dff["Date (Day)"] >= covid_start) &
                (dff["Date (Day)"] <= covid_end))]
    spread = dff.set_index("Date (Day)")["Spread"]   # refresh after drop


# ── 2. Layout grid ────────────────────────────────────────────────────
top = st.columns([2, 1])
bot = st.columns([2, 1])

# -- 2-A  overlay two legs --------------------------------------------
with top[0]:
    fig_legs = go.Figure()
    for col, clr in zip([near, far], ["#1f77b4", "#ff7f0e"]):
        fig_legs.add_trace(go.Scatter(
            x=dff["Date (Day)"], y=dff[col], name=col,
            mode="lines", line=dict(color=clr)
        ))
    fig_legs.update_layout(title="Outrights overlay", hovermode="x unified")
    st.plotly_chart(fig_legs, use_container_width=True)

# -- 2-B  numeric summary ---------------------------------------------
with top[1]:
    stats = summary_stats(spread)

    labels = ["Last", "Mean", "Off Avg",
              "Median", "StDev", "StDev from Mean",
              "Percentile", "High", "Low"]

    cols = st.columns(3)
    for i, lab in enumerate(labels):
        val = stats[lab]
        if lab == "Percentile":
            fmt = f"{val:.1f}%"
        else:
            fmt = f"{val:.3f}"
        cols[i % 3].metric(lab, fmt)

    st.caption(
        f"High {stats['High Date']}  ·  "
        f"Low {stats['Low Date']}"
    )


# -- 2-C  spread time-series ------------------------------------------
with bot[0]:
    fig_spread = px.area(
        dff, x="Date (Day)", y="Spread",
        labels={"Spread": spread_name},
        title=f"{spread_name} over time"
    )
    fig_spread.add_hline(stats["Mean"], line_dash="dash", line_color="gray")
    fig_spread.update_layout(hovermode="x unified")
    st.plotly_chart(fig_spread, use_container_width=True)

# -- 2-D  histogram ----------------------------------------------------
with bot[1]:
    fig_hist = px.histogram(
        spread, nbins=60, opacity=0.75,
        labels={"value": "Spread ($/bbl)"},
        title="Distribution"
    )
    fig_hist.add_vline(stats["Mean"], line_dash="dash", line_color="gray",
                       annotation_text="Mean", annotation_position="top left")
    st.plotly_chart(fig_hist, use_container_width=True)
