"""
nn_features.py  – build a clean, numeric feature matrix
-------------------------------------------------------
Called once per upload → cached.

Output
------
X : pandas.DataFrame  (index = calendar date)
      • numeric z‑scored columns ready for distance search
meta : pandas.DataFrame  (index = same, cols = headline vars you want to
      show in neighbour table – e.g. Prompt Spread, Dec Red, Cushing)

You can add / drop engineered features in `FEATURE_FUNCS`.
"""

import pandas as pd, numpy as np
from typing import Dict, Callable

# ------------------------------------------------------------
# Feature builders – each returns a pd.Series (must align on index)
# ------------------------------------------------------------
def fwd_curve_slopes(df: pd.DataFrame) -> pd.DataFrame:
    """M1‑M3, M3‑M6, M6‑M12 $/bbl slopes."""
    return pd.DataFrame({
        "Slope_1_3":  df["%CL 1!"] - df["%CL 3!"],
        "Slope_3_6":  df["%CL 3!"] - df["%CL 6!"],
        "Slope_6_12": df["%CL 6!"] - df["%CL 12!"],
    })

def curve_level_z(df: pd.DataFrame) -> pd.DataFrame:
    """z‑score of each outright vs 3‑yr window."""
    outs = [c for c in df.columns if c.startswith("%CL ")]
    z = (df[outs] - df[outs].rolling(756, min_periods=60).mean()) / \
        df[outs].rolling(756, min_periods=60).std()
    z.columns = [c + "_z" for c in outs]
    return z

def cushing_momentum(df: pd.DataFrame) -> pd.Series:
    return df["Cushing Stocks (Mbbl) (Interp)"].diff(7).rename("ΔCush_1w")

# register
FEATURE_FUNCS: Dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    "slopes": fwd_curve_slopes,
    "level_z": curve_level_z,
    "cush_mom": cushing_momentum,
}

HEADLINE_COLS = ["Prompt Spread", "Dec Red", "Cushing Stocks (Interp)"]

# ------------------------------------------------------------
def build_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns
    -------
    X   : feature matrix (z‑scored per column, NaNs dropped)
    meta: selected headline columns (not scaled) for neighbour table
    """
    feats = []
    for f in FEATURE_FUNCS.values():
        part = f(df)
        feats.append(part)

    X = pd.concat(feats, axis=1)

    # z‑score each feature (some already, but cheap to redo)
    X = (X - X.mean()) / X.std()

    # drop rows with any NaN (rare after your ffill/bfill)
    X = X.dropna()

    meta = df.loc[X.index, HEADLINE_COLS]

    return X, meta
