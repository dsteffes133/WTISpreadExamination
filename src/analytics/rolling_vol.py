import pandas as pd

def rolling_vol(
    df: pd.DataFrame,
    cols: list[str],
    window: int = 20,
    annualize: bool = True,
) -> pd.DataFrame:
    """
    Return DataFrame of rolling stdevs (% change) for chosen columns.
    df must have a 'Date (Day)' column.
    """
    pct = df.set_index("Date (Day)")[cols].pct_change()
    vol = pct.rolling(window).std()
    if annualize:
        vol *= (252**0.5)
    vol = vol.dropna()
    vol = vol.reset_index()
    return vol
