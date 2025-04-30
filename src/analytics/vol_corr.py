import pandas as pd

def rolling_abs_corr(
    df: pd.DataFrame,
    cols: list[str],
    window: int = 20,
) -> pd.DataFrame:
    """
    Rolling correlation of absolute % returns over `window` days.

    Returns a correlation matrix (DataFrame) for the **latest** window.
    """
    pct = df.set_index("Date (Day)")[cols].pct_change().abs()
    latest_window = pct.tail(window)
    # drop cols that are all-NaN over the window (rare)
    latest_window = latest_window.dropna(axis=1, how="all")
    return latest_window.corr()
