"""
nn_features.py  – build a clean, numeric feature matrix
-------------------------------------------------------
*Called once per upload — cached by Streamlit*

Returns
-------
X     : DataFrame (index = calendar days) of z‑scored features
meta  : DataFrame of headline columns for neighbour table
"""

from __future__ import annotations
import pandas as pd, numpy as np
from typing import Dict, Callable, List

# ── feature builders ──────────────────────────────────────────────────
def fwd_curve_slopes(df: pd.DataFrame) -> pd.DataFrame:
    """M1‑M3, M3‑M6, M6‑M12 $/bbl slopes."""
    return pd.DataFrame({
        "Slope_1_3":  df["%CL 1!"] - df["%CL 3!"],
        "Slope_3_6":  df["%CL 3!"] - df["%CL 6!"],
        "Slope_6_12": df["%CL 6!"] - df["%CL 12!"],
    })

def curve_level_z(df: pd.DataFrame) -> pd.DataFrame:
    """z‑score of each outright vs 3‑yr window (756 ≈ 3*252)."""
    outs = [c for c in df.columns if c.startswith("%CL ")]
    roll_mean = df[outs].rolling(756, min_periods=60).mean()
    roll_std  = df[outs].rolling(756, min_periods=60).std()
    z = (df[outs] - roll_mean) / roll_std
    z.columns = [c + "_z" for c in outs]
    return z

def cushing_momentum(df: pd.DataFrame) -> pd.Series:
    """
    1‑week ΔCushing using the Interp series if present,
    else the Release or raw column.
    """
    for cand in ["Cushing Stocks (Mbbl) (Interp)",
                 "Cushing Stocks (Interp)",
                 "Cushing Stocks (Mbbl) (Release)",
                 "Cushing Stocks (Mbbl)"]:
        if cand in df.columns:
            return df[cand].diff(7).rename("ΔCush_1w")
    # fallback empty series (gets dropped later)
    return pd.Series(dtype=float, name="ΔCush_1w")

FEATURE_FUNCS: Dict[str, Callable[[pd.DataFrame], pd.DataFrame | pd.Series]] = {
    "slopes":    fwd_curve_slopes,
    "level_z":   curve_level_z,
    "cush_mom":  cushing_momentum,
}

# headline columns shown in the neighbour table (keep if present)
HEADLINE_CANDIDATES: List[str] = [
    "Prompt Spread",
    "Dec Red",
    "Cushing Stocks (Mbbl) (Interp)",
    "Cushing Stocks (Interp)",
    "Cushing Stocks (Mbbl) (Release)",
]

# ── main builder ──────────────────────────────────────────────────────
def build_feature_matrix(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Parameters
    ----------
    df : fully engineered `daily_df`

    Returns
    -------
    X    : z‑scored feature DataFrame (no NaNs)
    meta : headline columns for neighbour report (not scaled)
    """
    feat_parts = []
    for func in FEATURE_FUNCS.values():
        part = func(df)
        feat_parts.append(part)

    X = pd.concat(feat_parts, axis=1)

    # z‑score each column (guard against division by 0)
    X = (X - X.mean()) / X.std().replace(0, np.nan)

    # drop rows with any NaN (rare after ffill/bfill)
    X = X.dropna()

    # build meta with only the columns that exist
    present = [c for c in HEADLINE_CANDIDATES if c in df.columns]
    meta = df.loc[X.index, present]

    return X, meta
