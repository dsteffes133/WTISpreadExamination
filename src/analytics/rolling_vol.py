import pandas as pd
import numpy as np
from typing import List

def rolling_vol(
    df: pd.DataFrame,
    cols: List[str],
    window: int = 20,
    annualize: bool = True,
    min_periods: int | None = None,
) -> pd.DataFrame:
    """
    Rolling volatility (% daily returns) for given columns.

    Parameters
    ----------
    df : DataFrame with a 'Date (Day)' column
    cols : list of columns to calculate vol for
    window : look‑back length (default 20)
    annualize : if True multiply by sqrt(252)
    min_periods : minimum non‑NA observations inside the window
                  (default = window → classic behaviour)

    Returns
    -------
    DataFrame with the same date index, no rows dropped.
    """
    if min_periods is None:
        min_periods = window

    pct = df.set_index("Date (Day)")[cols].pct_change()

    vol = pct.rolling(window=window, min_periods=min_periods).std()
    if annualize:
        vol *= np.sqrt(252)

    vol.reset_index(inplace=True)
    return vol
