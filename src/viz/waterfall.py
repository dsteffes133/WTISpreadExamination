import plotly.graph_objects as go
import pandas as pd
from src.analytics.term_structure import list_legs

def waterfall_curve(df: pd.DataFrame, idx: int,
                    threshold: float = 0.20, max_leg: int = 12):
    """
    Compare row idx-1 vs idx (overnight), colouring segments whose absolute
    change > threshold. Assumes df has a 'Date (Day)' column.
    """
    legs = list_legs(df, max_leg)

    # work with an indexed copy so row slicing returns Series of legs only
    dfi = df.set_index("Date (Day)").sort_index()

    prev = dfi.iloc[idx - 1][legs]
    curr = dfi.iloc[idx][legs]
    delta = curr - prev

    colours = [
        "green" if d > threshold else
        "red"   if d < -threshold else
        "gray"
        for d in delta
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[int(l.split()[1][:-1]) for l in legs],
        y=prev,
        mode="lines+markers",
        name=str(prev.name.date()),
        line=dict(color="gray", width=1, dash="dot")
    ))
    fig.add_trace(go.Scatter(
        x=[int(l.split()[1][:-1]) for l in legs],
        y=curr,
        mode="lines+markers",
        marker=dict(color=colours, size=10),
        name=str(curr.name.date()),
        line=dict(width=2)
    ))
    fig.update_layout(
        xaxis_title="M-leg",
        yaxis_title="Price ($/bbl)",
        height=400,
        hovermode="x unified"
    )
    return fig
