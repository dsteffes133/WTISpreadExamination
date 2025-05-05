import plotly.express as px, pandas as pd

def neighbour_table(meta: pd.DataFrame, dist: pd.Series):
    tbl = meta.copy()
    tbl["Distance"] = dist
    return tbl.sort_values("Distance")

def outcome_bar(mean_ret: pd.Series):
    fig = px.bar(mean_ret, y=mean_ret.values, labels={"index": "Spread",
                                                      "y": "Avg Δ ($/bbl)"})
    fig.update_layout(height=300)
    return fig
