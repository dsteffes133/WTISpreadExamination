"""
Compute forward Δ and Sharpe for each neighbour.
"""

import pandas as pd, numpy as np
from typing import List

def forward_outcomes(df: pd.DataFrame,
                     neighbours: pd.Index,
                     target_cols: List[str],
                     fwd_days: int = 10):
    """
    Returns wide DataFrame: rows = neighbour date,
    columns = each target spread's forward return.
    """
    outcomes = {}
    for t in neighbours:
        t0 = df.index.get_loc(t)
        tF = t0 + fwd_days
        if tF >= len(df):
            continue  # neighbour too close to end
        ret = (df[target_cols].iloc[tF] - df[target_cols].iloc[t0])   # abs Δ
        outcomes[t] = ret
    return pd.DataFrame(outcomes).T
