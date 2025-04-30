import plotly.express as px
import pandas as pd

def corr_heatmap(corr_df: pd.DataFrame):
    fig = px.imshow(
        corr_df,
        text_auto=".2f",
        color_continuous_scale="Purples",
        zmin=0, zmax=1,
        aspect="auto",
        labels=dict(color="Corr |r|")
    )
    # tighten layout
    fig.update_layout(height=600, margin=dict(l=40, r=40, t=40, b=40))
    return fig
