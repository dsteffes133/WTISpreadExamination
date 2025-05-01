# src/viz/waterfall.py
import re
import plotly.graph_objects as go
import pandas as pd
from src.analytics.term_structure import list_legs

_NUMERIC_LEG = re.compile(r"%CL (\d+)!")           # keeps %CL 1! … %CL 24!

def _numeric_legs(df: pd.DataFrame, max_leg: int) -> list[str]:
    """Return ['%CL 1!', …] up to max_leg that actually exist in df."""
    legs = [c for c in list_legs(df, max_leg) if _NUMERIC_LEG.fullmatch(c)]
    return legs

def waterfall_curve(
    df: pd.DataFrame,
    idx: int,
    threshold: float = 0.20,
    max_leg: int = 12
) -> go.Figure | None:
    """
    Plot yesterday vs today forward-curve with coloured markers.
    • Only %CL n! legs (1-max_leg) are shown; calendar codes like "CL Z25"
      are ignored to avoid int() parsing errors.
    • Segments whose |Δ| > threshold ($/bbl) are coloured
      green (up) or red (down); others gray.
    """
    legs = _numeric_legs(df, max_leg)
    if len(legs) < 2 or idx == 0:
        return None                      # nothing to plot or idx out of range

    # assure we have a date index
    dfi = df.set_index("Date (Day)").sort_index()

    # guard idx bounds
    if idx >= len(dfi):
        idx = len(dfi) - 1
    prev, curr = dfi.iloc[idx - 1], dfi.iloc[idx]

    prev_leg = prev[legs]
    curr_leg = curr[legs]
    delta    = curr_leg - prev_leg

    # colours per leg
    colours = [
        "green" if d > threshold else
        "red"   if d < -threshold else
        "gray"
        for d in delta
    ]

    x_vals = list(range(1, len(legs) + 1))     # 1-, 2-, 3-… axis

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_vals, y=prev_leg,
        mode="lines+markers",
        name=str(prev.name.date()),
        line=dict(color="gray", width=1, dash="dot")
    ))
    fig.add_trace(go.Scatter(
        x=x_vals, y=curr_leg,
        mode="lines+markers",
        name=str(curr.name.date()),
        marker=dict(color=colours, size=10),
        line=dict(width=2)
    ))

    fig.update_layout(
        xaxis_title="M-leg",
        yaxis_title="Price ($/bbl)",
        hovermode="x unified",
        height=400,
        showlegend=True
    )
    return fig
