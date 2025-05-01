# src/viz/curve.py
import plotly.graph_objects as go
import pandas as pd
from src.analytics.term_structure import list_legs

# src/viz/curve.py
import plotly.graph_objects as go
import pandas as pd
import re
from src.analytics.term_structure import list_legs

_NUM_RE = re.compile(r"%CL (\d+)!")    # keep only numeric legs

def make_curve_figure(df: pd.DataFrame, date: pd.Timestamp, max_leg: int = 12):
    # pick only %CL n! legs
    legs = [c for c in list_legs(df, max_leg) if _NUM_RE.fullmatch(c)]
    y = df.loc[date, legs].ffill().bfill()

    # x-axis = sequential M-leg number (1-, 2-, …)
    x = list(range(1, len(legs) + 1))

    # colour by slope sign
    colours = ["green"]
    colours += ["green" if y.iloc[i] > y.iloc[i+1] else "red"
                for i in range(len(y) - 1)]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x, y=y,
            mode="lines+markers",
            marker=dict(color=colours, size=10),
            line=dict(width=2),
            name=str(date.date())
        )
    )
    fig.update_layout(
        xaxis_title="Contract Month (M-leg)",
        yaxis_title="Price ($/bbl)",
        hovermode="x unified",
        showlegend=False
    )
    return fig
