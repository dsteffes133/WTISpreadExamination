import plotly.express as px
import pandas as pd

def beta_heatmap(beta_df: pd.DataFrame):
    """Heat-map: rows = instruments, colors = β."""
    fig = px.imshow(
        beta_df[["beta"]],
        color_continuous_scale="RdBu",
        aspect="auto",
        zmin=-beta_df["beta"].abs().max(),
        zmax=beta_df["beta"].abs().max(),
        labels=dict(x="", y="", color="β ($/bbl per Mbbl)")
    )
    fig.update_yaxes(autorange="reversed")
    return fig
