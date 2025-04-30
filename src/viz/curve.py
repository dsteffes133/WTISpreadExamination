# src/viz/curve.py
import plotly.graph_objects as go
import pandas as pd
from src.analytics.term_structure import list_legs

def make_curve_figure(df: pd.DataFrame, date: pd.Timestamp, max_leg: int = 12):
    legs = list_legs(df, max_leg)
    y = df.loc[date, legs].ffill().bfill()        # ensure no NaNs

    # colour by slope sign
    colours = ['green']                           # first point dummy
    colours += ['green' if y[i] > y[i+1] else 'red'
                for i in range(len(y) - 1)]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[int(l.split()[1][:-1]) for l in legs],
            y=y,
            mode="lines+markers",
            line=dict(width=2),
            marker=dict(color=colours, size=10),
            name=str(date.date()),
        )
    )
    fig.update_layout(
        xaxis_title="Contract Month (M-leg)",
        yaxis_title="Price (USD/bbl)",
        hovermode="x unified",
        showlegend=False
    )
    return fig
