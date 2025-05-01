# src/analytics/term_structure.py
import pandas as pd
import re

_LEG_RE_PCT = re.compile(r"%CL (\d+)!")            # %CL 1! … %CL 24!
_LEG_RE_CAL = re.compile(r"CL [FGHJKMNQUVXZ]\d{2}") # e.g. CL Z25

def list_legs(df, max_pct_leg=24):
    pct_legs = [
        c for c in df.columns
        if _LEG_RE_PCT.fullmatch(c) and int(_LEG_RE_PCT.fullmatch(c).group(1)) <= max_pct_leg
    ]
    cal_legs = [c for c in df.columns if _LEG_RE_CAL.fullmatch(c)]
    return sorted(pct_legs, key=lambda c: int(_LEG_RE_PCT.fullmatch(c).group(1))) + sorted(cal_legs)

def curve_on_date(df: pd.DataFrame, date: pd.Timestamp, max_leg: int = 12):
    """Return Series of curve values for the chosen date."""
    legs = list_legs(df, max_leg)
    row = df.loc[date, legs]
    # if date isn’t trading day → forward-fill so slider shows last known curve
    return row.ffill().bfill()

# src/analytics/term_structure.py  (add)
def kink_radar(df: pd.DataFrame, lookback=90, max_leg=12):
    legs = list_legs(df, max_leg)
    diff = df.set_index("Date (Day)")[legs].diff()
    z = (diff - diff.rolling(60).mean()) / diff.rolling(60).std()
    z = z.tail(lookback).clip(-3, 3)        # bound so colours pop
    return z
