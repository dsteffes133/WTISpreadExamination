# ── src/preprocessing/daily.py  ────────────────────────────────────────────
"""
Load *David WTI Spread Analysis.xlsx* and return a single **daily_df**
that already contains

* all %CL outrights and legacy spreads
* December outrights CL Z18 … CL Z28
* dynamic colour spreads (Dec Red, Red/Blue, Blue/Green) that roll each 1 Jan
* Cushing Stocks (Release / Interp)
* every column in **“EIA WEEKLY DATA”** stamped both as (Release) and (Interp)
"""

from pathlib import Path
import pandas as pd, re
from itertools import combinations
import numpy as np
import pandas_market_calendars as mcal   # still used later if you add trading-day filter

# ── helpers ───────────────────────────────────────────────────────────────
_CL_NUM_RE = re.compile(r"%CL (\d+)!")          # %CL 1! … 24!
_Z_CON_RE  = re.compile(r"CL Z\d{2}$")          # CL Z18 … Z28

def _dec_contract(year: int) -> str:
    """Return column label for a given December contract year."""
    return f"CL Z{str(year)[-2:]}"

def _next_wed(d: pd.Timestamp) -> pd.Timestamp:
    """First Wednesday *after* date d (never same-day)."""
    off = (2 - d.weekday() + 7) % 7
    return d + pd.Timedelta(days=off or 7)


# ── main loader ───────────────────────────────────────────────────────────
def load_daily_xlsx(
    xlsx: str | Path,
    daily_sheet: str = "Daily Data",
    weekly_sheet: str = "EIA WEEKLY DATA",
    max_leg: int = 24,
    cushing_capacity_mbbl: float | None = None,   # if you later need utilisation
) -> pd.DataFrame:

    # 1 ── read Daily sheet (no col limit → captures new Z contracts) ------
    df = pd.read_excel(
        xlsx, daily_sheet,
        skiprows=5, header=0              # first 5 lines are headers
        # usecols removed to auto-include new columns
    )
    df.columns = df.columns.str.strip()   # trim stray spaces

    # 2 ── build every %CL outrights & intra-curve spreads ---------------
    cl_cols = [c for c in df.columns if _CL_NUM_RE.fullmatch(c)]
    cl_cols.sort(key=lambda c: int(_CL_NUM_RE.fullmatch(c).group(1)))

    for near, far in combinations(cl_cols, 2):
        df[f"{near} - {far}"] = df[near] - df[far]

    # 3 ── dynamic colour spreads (Dec Red / Red-Blue / Blue-Green) ------
    df["YearTmp"] = pd.to_datetime(df["Date (Day)"]).dt.year

    for name, o1, o2 in [("Dec Red", 0, 1), ("Red/Blue", 1, 2),
                         ("Blue/Green", 2, 3)]:

        lhs_cols = [_dec_contract(y + o1) for y in df["YearTmp"]]
        rhs_cols = [_dec_contract(y + o2) for y in df["YearTmp"]]

        # map the column names to positional indices (-1 if missing)
        col_lut = {c: i for i, c in enumerate(df.columns)}
        lhs_idx = np.array([col_lut.get(c, -1) for c in lhs_cols])
        rhs_idx = np.array([col_lut.get(c, -1) for c in rhs_cols])

        mat = df.to_numpy()                         # full data matrix
        row = np.arange(len(df))

        lhs_vals = np.where(lhs_idx >= 0, mat[row, lhs_idx], np.nan)
        rhs_vals = np.where(rhs_idx >= 0, mat[row, rhs_idx], np.nan)

        df[name] = lhs_vals - rhs_vals

    df.drop(columns="YearTmp", inplace=True, errors="ignore")

    # 4 ── bring Date to index & sort -------------------------------------
    df["Date (Day)"] = pd.to_datetime(df["Date (Day)"])
    df = df.set_index("Date (Day)").sort_index()

    # 5 ── Cushing Stocks handling ----------------------------------------
    if "Cushing Stocks (Mbbl)" in df.columns:
        cush_weekly = df["Cushing Stocks (Mbbl)"].dropna()
    else:
        # fallback: read from weekly sheet later
        cush_weekly = None

    # 6 ── read EIA WEEKLY DATA sheet -------------------------------------
    weekly = pd.read_excel(
        xlsx, weekly_sheet,
        skiprows=2, header=0, usecols="A:P"
    )
    weekly.rename(columns={weekly.columns[0]: "Date"}, inplace=True)
    weekly["Date"] = pd.to_datetime(weekly["Date"])
    weekly = weekly.set_index("Date").sort_index()

    if cush_weekly is None and "Cushing Stocks (Mbbl)" in weekly.columns:
        cush_weekly = weekly["Cushing Stocks (Mbbl)"].dropna()

    # helper to stamp weekly series onto daily frame
    def _add_weekly(series: pd.Series, label: str):
        # (a) Release: move to next Wednesday and f-fill
        rel = series.copy(); rel.index = rel.index.map(_next_wed)
        df[f"{label} (Release)"] = rel.reindex(df.index).ffill()

        # (b) Interp: linear Fri-to-Fri
        interp = (series.reindex(df.index)
                        .interpolate("time")
                        .ffill().bfill())
        df[f"{label} (Interp)"] = interp

    for col in weekly.columns:
        _add_weekly(weekly[col].dropna(), col)

    # also apply to Cushing if not in weekly loop
    if cush_weekly is not None and "Cushing Stocks (Mbbl) (Release)" not in df.columns:
        _add_weekly(cush_weekly, "Cushing Stocks (Mbbl)")

    # 7 ── forward-fill price-like columns --------------------------------
    price_cols = [c for c in df.columns
                  if _CL_NUM_RE.fullmatch(c) or _Z_CON_RE.fullmatch(c)
                  or " - " in c]           # spreads
    df[price_cols] = df[price_cols].ffill()

    # 8 ── reindex to full calendar ---------------------------------------
    full_idx = pd.date_range(df.index.min(), df.index.max(), freq="D")
    df = df.reindex(full_idx)
    df[price_cols] = df[price_cols].ffill()  # f-fill the gap days

    # 9 ── tidy & return ---------------------------------------------------
    df.reset_index(inplace=True)
    df.rename(columns={"index": "Date (Day)"}, inplace=True)
    return df
