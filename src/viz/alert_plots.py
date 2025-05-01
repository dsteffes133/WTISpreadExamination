# src/viz/alert_plots.py
import pandas as pd
import plotly.graph_objects as go

def plot_alert_ts(alert_name: str, ts):
    """
    Generic helper for the Alerts page.
    * ts may be a Series (e.g., spread history) or DataFrame (e.g., many legs).
    * Adds reference lines for certain alerts.
    """
    if isinstance(ts, pd.Series):
        df = ts.to_frame(name="value")
    else:
        df = ts.copy()

    fig = go.Figure()

    # --- Single-series (most alerts) -----------------------------------
    if df.shape[1] == 1:
        col = df.columns[0]
        fig.add_trace(go.Scatter(x=df.index, y=df[col],
                                 mode="lines", name=col))

        # extra context per alert
        if alert_name == "Prompt":
            mu = df[col].iloc[:-1].mean()
            sigma = df[col].iloc[:-1].std()
            for k in (-2, 2):
                fig.add_hline(mu + k*sigma, line_dash="dash", line_color="gray")
        elif alert_name == "DecRed":
            fig.add_hline(0, line_dash="dash", line_color="gray",
                          annotation_text="Mean")

    # --- Multi-series (kink radar) ------------------------------------
    else:
        for col in df.columns:
            fig.add_trace(go.Bar(x=[col], y=[df[col].iloc[-1]],
                                 name=col))

    fig.update_layout(
        title=f"{alert_name} context",
        hovermode="x unified",
        height=300,
        margin=dict(l=40, r=20, t=40, b=40)
    )
    return fig
