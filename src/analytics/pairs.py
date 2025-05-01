import numpy as np, pandas as pd, statsmodels.api as sm
from itertools import combinations

# ------------------------------------------------------------------ #
def pair_data(df: pd.DataFrame, x_col: str, y_col: str, beta: float | None):
    """Return aligned Series X, Y and hedge β (OLS if None)."""
    xy = df[[x_col, y_col]].dropna()
    if beta is None:
        beta = sm.OLS(xy[y_col], sm.add_constant(xy[x_col])).fit().params[x_col]
    return xy[x_col], xy[y_col], beta

# ------------------------------------------------------------------ #
def engle_granger(df, x_col, y_col):
    """β, p-value, residual Series (y − (α+βx))."""
    xy = df[[x_col, y_col]].dropna()
    model = sm.OLS(xy[y_col], sm.add_constant(xy[x_col])).fit()
    beta  = model.params[x_col]
    alpha = model.params["const"]
    resid = xy[y_col] - (alpha + beta * xy[x_col])    # subtract α too
    pval  = sm.tsa.stattools.adfuller(resid, maxlag=1, regression="n")[1]
    return beta, pval, resid


# ------------------------------------------------------------------ #
def zscore(s: pd.Series, lookback=60):
    mu = s.rolling(lookback).mean()
    sd = s.rolling(lookback).std()
    return (s - mu) / sd

# ------------------------------------------------------------------ #
def backtest(df, x_col, y_col,
             entry_z=2.0, exit_z=0.5,
             beta_window=90, roll_window=60):
    """
    Simple z-score mean-reversion back-test.
    Return equity curve dataframe.
    """
    xy = df[[x_col, y_col]].dropna().copy()
    # rolling hedge
    beta = (
        xy[y_col].rolling(beta_window).cov(xy[x_col]) /
        xy[x_col].rolling(beta_window).var()
    )
    resid = xy[y_col] - beta * xy[x_col]
    z = zscore(resid, roll_window)
    pos = np.where(z > entry_z, -1, np.where(z < -entry_z, 1, np.nan))
    pos = pd.Series(pos, index=xy.index).ffill().where(z.abs() > exit_z, 0).ffill().fillna(0)

    ret = pos.shift() * (xy[y_col].pct_change() - beta * xy[x_col].pct_change())
    equity = (1 + ret).cumprod()

    return pd.DataFrame({"pos": pos, "equity": equity, "z": z})

# ------------------------------------------------------------------ #
def batch_scan(df, universe, p_thres=0.05, z_thres=2.0):
    """Return DataFrame of pairs with |z| > z_thres & p < p_thres."""
    results = []
    for x, y in combinations(universe, 2):
        try:
            β, p, resid = engle_granger(df, x, y)
        except Exception:
            continue
        if np.isnan(p) or p > p_thres:
            continue
        z_now = zscore(resid).iloc[-1]
        if abs(z_now) >= z_thres:
            results.append({"X": x, "Y": y, "β": β, "ADF_p": p, "z": z_now})
    return pd.DataFrame(results).sort_values("z", key=np.abs, ascending=False)
