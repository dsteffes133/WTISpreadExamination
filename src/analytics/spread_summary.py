import pandas as pd, numpy as np
from scipy import stats

def compute_spread(df: pd.DataFrame, near: str, far: str) -> pd.Series:
    return df[near] - df[far]

def summary_stats(spread: pd.Series):
    s = spread.dropna()
    last = s.iloc[-1]
    mean = s.mean()
    std  = s.std()
    stats_dict = {
        "Last":           last,
        "Mean":           mean,
        "Off Avg":        last - mean,
        "Median":         s.median(),
        "StDev":          std,
        "StDev from Mean": (last - mean) / std if std else np.nan,
        "Percentile":     stats.percentileofscore(s, last),
        "High":           s.max(),
        "High Date":      s.idxmax().date(),
        "Low":            s.min(),
        "Low Date":       s.idxmin().date(),
    }
    return pd.Series(stats_dict)
