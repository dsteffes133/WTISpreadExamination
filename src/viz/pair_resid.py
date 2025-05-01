import plotly.graph_objects as go, pandas as pd

def resid_chart(resid: pd.Series):
    z = (resid - resid.rolling(60).mean())/resid.rolling(60).std()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=resid.index, y=z, mode='lines', name='z-score'))
    for k, col in zip([1,2], ['lightgray','lightgray']):
        fig.add_hline(k, line=dict(color=col, dash='dash'))
        fig.add_hline(-k, line=dict(color=col, dash='dash'))
    fig.update_layout(title="Residual z-score", yaxis_title='z')
    return fig
