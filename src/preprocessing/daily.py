"""
daily.py  –  single‑frame pre‑processor

* Reads **Daily Data** sheet (all columns, skip first 5 rows)
* Builds every intra‑%CL spread
* Rebuilds Prompt Spread if absent
* Adds December‑colour spreads (Dec Red, Red/Blue, Blue/Green) that
  roll automatically each 1 Jan
* Reads **EIA WEEKLY DATA** sheet (rows 3‑∞, A:P) and, for every column:
      • <name> (Release)  – value stamped to next Wednesday, f‑fill
      • <name> (Interp)   – linear Fri‑to‑Fri interpolation
* Same Release/Interp treatment for Cushing if only found in weekly sheet
* Returns a fully‑daily DataFrame ready for the dashboard
"""

from pathlib import Path
import pandas as pd, numpy as np
import re
from itertools import combinations

# ── regex helpers -----------------------------------------------------
_CL_NUM = re.compile(r"%CL (\d+)!")      # %CL 1! … %CL 24!
_Z_CON  = re.compile(r"CL Z\d{2}$")      # CL Z18 … CL Z28


# ── util --------------------------------------------------------------
def _dec_contract(year: int) -> str:
    return f"CL Z{str(year)[-2:]}"       # 2025→CL Z25

def _next_wed(ts: pd.Timestamp) -> pd.Timestamp:
    """First Wed *after* ts (never same‑day)."""
    off = (2 - ts.weekday() + 7) % 7
    return ts + pd.Timedelta(days=off or 7)


# ── loader ------------------------------------------------------------
def load_daily_xlsx(
    xlsx: str | Path,
    daily_sheet: str = "Daily Data",
    weekly_sheet: str = "EIA WEEKLY DATA",
    max_leg: int = 24,
) -> pd.DataFrame:

    # 1) Daily sheet – read EVERYTHING (captures new columns)
    df = pd.read_excel(
        xlsx, daily_sheet,
        skiprows=5, header=0,           # headers begin row 6
    )
    df.columns = df.columns.str.strip()

    # 2) Build all %CL intra‑curve spreads
    cl_cols = [c for c in df.columns if _CL_NUM.fullmatch(c)]
    cl_cols.sort(key=lambda c: int(_CL_NUM.fullmatch(c).group(1)))
    for n, f in combinations(cl_cols, 2):
        df[f"{n} - {f}"] = df[n] - df[f]

    # 3) Rebuild Prompt Spread if missing
    if "Prompt Spread" not in df.columns and \
       "%CL 1!" in df.columns and "%CL 2!" in df.columns:
        df["Prompt Spread"] = df["%CL 1!"] - df["%CL 2!"]

    # 4) December colour spreads (vectorised, pandas‑agnostic)
    df["__YearTmp"] = pd.to_datetime(df["Date (Day)"]).dt.year
    for name, o1, o2 in [("Dec Red", 0, 1),
                         ("Red/Blue", 1, 2),
                         ("Blue/Green", 2, 3)]:
        lhs_cols = [_dec_contract(y + o1) for y in df["__YearTmp"]]
        rhs_cols = [_dec_contract(y + o2) for y in df["__YearTmp"]]

        col_lut = {c: i for i, c in enumerate(df.columns)}
        lhs_idx = np.array([col_lut.get(c, -1) for c in lhs_cols])
        rhs_idx = np.array([col_lut.get(c, -1) for c in rhs_cols])

        mat = df.to_numpy()
        row = np.arange(len(df))
        lhs_vals = np.where(lhs_idx >= 0, mat[row, lhs_idx], np.nan)
        rhs_vals = np.where(rhs_idx >= 0, mat[row, rhs_idx], np.nan)
        df[name] = lhs_vals - rhs_vals
    df.drop(columns="__YearTmp", inplace=True, errors="ignore")

    # 5) Index by date
    df["Date (Day)"] = pd.to_datetime(df["Date (Day)"])
    df = df.set_index("Date (Day)").sort_index()

    # 6) Weekly sheet  →  Release & Interp columns
    weekly = pd.read_excel(
        xlsx, weekly_sheet,
        skiprows=2, header=0, usecols="A:P"
    )
    weekly.rename(columns={weekly.columns[0]: "Date"}, inplace=True)
    weekly["Date"] = pd.to_datetime(weekly["Date"])
    weekly = weekly.set_index("Date").sort_index()

    def _add_weekly(series: pd.Series, label: str):
        # Release
        rel = series.copy(); rel.index = rel.index.map(_next_wed)
        df[f"{label} (Release)"] = rel.reindex(df.index).ffill()
        # Interp
        interp = (series.reindex(df.index)
                          .interpolate("time")
                          .ffill().bfill())
        df[f"{label} (Interp)"] = interp

    for col in weekly.columns:
        _add_weekly(weekly[col].dropna(), col)

    # if Cushing not in daily sheet, pull from weekly
    if "Cushing Stocks (Mbbl)" not in df.columns and \
       "Cushing Stocks (Mbbl)" in weekly.columns:
        _add_weekly(weekly["Cushing Stocks (Mbbl)"].dropna(),
                    "Cushing Stocks (Mbbl)")

    # 7) Forward‑fill price‑like columns
    price_like = [c for c in df.columns
                  if _CL_NUM.fullmatch(c)
                  or _Z_CON.fullmatch(c)
                  or " - " in c]
    df[price_like] = df[price_like].ffill()

    # 8) Calendar reindex to fill holidays/weekends
    full = pd.date_range(df.index.min(), df.index.max(), freq="D")
    df = df.reindex(full)
    df[price_like] = df[price_like].ffill()

    # 9) Return tidy frame
    df.reset_index(inplace=True)
    df.rename(columns={"index": "Date (Day)"}, inplace=True)
    return df
