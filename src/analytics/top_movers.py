import pandas as pd
from .term_structure import list_legs

def top_movers(df: pd.DataFrame, window: int = 60,
               max_leg: int = 12, k: int = 5) -> pd.DataFrame:
    """
    Return a DataFrame of the k biggest |z-score| movers on the last row.
    """
    legs = list_legs(df, max_leg)
    diff = df.set_index("Date (Day)")[legs].diff()

    z = (diff - diff.rolling(window).mean()) / diff.rolling(window).std()
    latest_z = z.iloc[-1].dropna().sort_values(key=lambda s: s.abs(),
                                               ascending=False)

    out = pd.DataFrame({
        "Δ price ($/bbl)": diff.iloc[-1][latest_z.index],
        "z-score": latest_z
    }).head(k)
    return out.reset_index(names="Leg")
