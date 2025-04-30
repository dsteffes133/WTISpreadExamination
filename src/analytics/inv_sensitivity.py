import pandas as pd
import statsmodels.api as sm
from typing import Dict

def calc_betas(df: pd.DataFrame,
               legs: list[str],
               spreads: list[str]) -> pd.DataFrame:
    """β, t-stat, R² of Δprice ~ ΔCushing (Wed releases only)."""

    wed = df[df["Date (Day)"].dt.weekday == 2].copy()
    wed["Δ Cush"] = df["Delta Cushing Release"].loc[wed.index]

    results: Dict[str, dict] = {}

    for col in legs + spreads:
        # build Δ-price column for this instrument
        wed["Δ price"] = df[col].diff().loc[wed.index]

        sample = wed[["Δ Cush", "Δ price"]].dropna()   # ← drop NaNs here
        if len(sample) < 10:                          # guard: too few obs
            results[col] = {"beta": float("nan"),
                            "t_stat": float("nan"),
                            "r2": float("nan")}
            continue

        x = sm.add_constant(sample["Δ Cush"])
        y = sample["Δ price"]
        model = sm.OLS(y, x).fit()

        results[col] = {
            "beta":  model.params["Δ Cush"],
            "t_stat": model.tvalues["Δ Cush"],
            "r2": model.rsquared
        }

    return pd.DataFrame(results).T