import plotly.express as px
import pandas as pd

def vol_panel(vol_df: pd.DataFrame, cols: list[str]):
    fig = px.line(
        vol_df,
        x="Date (Day)",
        y=cols,
        labels=dict(value="Rolling σ (ann., %)", variable="Series"),
    )
    fig.update_layout(legend=dict(orientation="h", y=-0.2))
    return fig
