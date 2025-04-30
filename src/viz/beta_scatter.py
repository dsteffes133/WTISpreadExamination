import plotly.express as px
import statsmodels.api as sm
import pandas as pd

def scatter_beta(df: pd.DataFrame, col: str):
    wed = df[df["Date (Day)"].dt.weekday == 2].copy()
    wed["Δ Cush"] = df["Delta Cushing Release"].loc[wed.index]
    wed["Δ price"] = df[col].diff().loc[wed.index]

    data = wed.dropna(subset=["Δ Cush", "Δ price"])
    x = sm.add_constant(data["Δ Cush"])
    beta = sm.OLS(data["Δ price"], x).fit().params["Δ Cush"]

    fig = px.scatter(
        data, x="Δ Cush", y="Δ price",
        trendline="ols",
        labels=dict(x="Δ Cushing (Mbbl)", y=f"Δ {col} ($/bbl)"),
        title=f"{col}: β={beta:.3f} $/bbl per Mbbl"
    )
    return fig
