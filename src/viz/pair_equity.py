# src/viz/pair_equity.py
import plotly.express as px, pandas as pd

def equity_chart(bt: pd.DataFrame):
    eq = bt["equity"].dropna()                 # remove leading NaNs
    if eq.empty:
        return None                            # caller can handle this
    fig = px.line(
        eq.reset_index(),                      # turn index into column
        x="index", y="equity",
        title="Back-test equity (notional 1-spread)",
        labels={"index": "Date", "equity": "Equity"}
    )
    return fig
