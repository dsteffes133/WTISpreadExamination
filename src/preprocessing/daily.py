# ─────────────────────────── src/preprocessing/daily.py ──────────────────────────
"""
Return **daily_df** ready for the dashboard.

Key features
------------
• Keeps only %CL 1–12 outrights, plus all CL Zyy December contracts  
• Builds every intra‑curve spread, and re‑creates **Prompt Spread** if absent  
• Adds rolling colour spreads: **Dec Red**, **Red / Blue**, **Blue / Green**  
• Ingests **EIA WEEKLY DATA** sheet — every weekly metric gets
    <metric> (Release)  – value stamped to the next Wed, f‑filled  
    <metric> (Interp)   – linear Friday‑to‑Friday interpolation  
• Cushing Stocks always has (Release) and (Interp) columns  
• Drops legacy helper columns and trims any future‑dated blank rows  
• All price‑like columns are coerced to numeric, zeros → NaN, then
  ffill + bfill so weekend rows carry the last trading‑day price.
"""

from pathlib import Path
import pandas as pd, numpy as np, re
from itertools import combinations

# ── helpers --------------------------------------------------------------------
_CL_NUM = re.compile(r"%CL (\d+)!")
_Z_CON  = re.compile(r"CL Z\d{2}$")

def _dec_contract(year: int) -> str:        # 2025 → "CL Z25"
    return f"CL Z{str(year)[-2:]}"

def _next_wed(ts: pd.Timestamp) -> pd.Timestamp:
    off = (2 - ts.weekday() + 7) % 7
    return ts + pd.Timedelta(days=off or 7)

# ── main loader ----------------------------------------------------------------
def load_daily_xlsx(
    xlsx: str | Path,
    daily_sheet: str = "Daily Data",
    weekly_sheet: str = "EIA WEEKLY DATA",
) -> pd.DataFrame:

    # 1 ▸ read Daily sheet
    df = pd.read_excel(xlsx, daily_sheet, skiprows=5, header=0)
    df.columns = df.columns.str.strip()

    # ── ensure the date column is called "Date (Day)" ───────────────────
    if "Date (Day)" not in df.columns:
        for c in df.columns:
            if c.lower().startswith("date"):
                df.rename(columns={c: "Date (Day)"}, inplace=True)
                break

    # ── drop %CL legs beyond 12
    far_legs = [c for c in df.columns
                if _CL_NUM.fullmatch(c) and int(_CL_NUM.fullmatch(c).group(1)) > 12]
    df.drop(columns=far_legs, inplace=True, errors="ignore")

    # ── drop legacy columns
    junk = {"Prompt TM", "Filter Range",
            "CL Settles / Fwd Proj (M1-M2)",
            "CL Settles / Fwd Proj (M2-M8)"}
    df.drop(columns=[c for c in df.columns if c.startswith("Unnamed:") or c in junk],
            inplace=True, errors="ignore")

    # ── coerce all price columns to numeric (stray text → NaN)
    price_cols_raw = [c for c in df.columns
                      if _CL_NUM.fullmatch(c) or _Z_CON.fullmatch(c)]
    df[price_cols_raw] = df[price_cols_raw].apply(
        pd.to_numeric, errors="coerce"
    )

    # 2 ▸ intra‑curve spreads
    cl_cols = sorted([c for c in df.columns if _CL_NUM.fullmatch(c)],
                     key=lambda c: int(_CL_NUM.fullmatch(c).group(1)))
    for near, far in combinations(cl_cols, 2):
        df[f"{near} - {far}"] = df[near] - df[far]

    

     # 5 ▸ index by date & trim future rows
    df["Date (Day)"] = pd.to_datetime(df["Date (Day)"])
    df = df.set_index("Date (Day)").sort_index()

    # ────────────────────────────────────────────────────────────────
    # COVID blackout  →  OPTION 2
    # Drop 2020‑03‑01 … 2020‑05‑31, then later re‑index + ffill/bfill
    covid_mask = df.loc["2020-03-01":"2020-05-31"].index
    df = df.drop(covid_mask)                       # *remove* the rows
    # ────────────────────────────────────────────────────────────────

    df = df.loc[:pd.Timestamp.today().normalize()]   # drop future blanks

    # 6 ▸ read EIA WEEKLY DATA
    weekly = pd.read_excel(xlsx, weekly_sheet, skiprows=2, header=0, usecols="A:P")
    weekly.rename(columns={weekly.columns[0]: "Date"}, inplace=True)
    weekly.columns = weekly.columns.str.strip()
    weekly["Date"] = pd.to_datetime(weekly["Date"])
    weekly = weekly.set_index("Date").sort_index()

    def _add_weekly(series: pd.Series, label: str):
        rel = series.copy(); rel.index = rel.index.map(_next_wed)
        df[f"{label} (Release)"] = rel.reindex(df.index).ffill()
        interp = (series.reindex(df.index).interpolate("time").ffill().bfill())
        df[f"{label} (Interp)"] = interp

    for col in weekly.columns:
        _add_weekly(weekly[col].dropna(), col)

    # ensure Cushing series exists
    if "Cushing Stocks (Mbbl)" in df.columns:
        _add_weekly(df["Cushing Stocks (Mbbl)"].dropna(), "Cushing Stocks (Mbbl)")
    elif "Cushing Stocks (Mbbl)" in weekly.columns:
        _add_weekly(weekly["Cushing Stocks (Mbbl)"].dropna(), "Cushing Stocks (Mbbl)")

    # 7 ▸ forward/back‑fill price‑like columns (zeros → NaN)
    special = ["Prompt Spread", "Dec Red", "Red/Blue", "Blue/Green"]
    price_like = [c for c in df.columns
                  if _CL_NUM.fullmatch(c) or _Z_CON.fullmatch(c)
                  or " - " in c or c in special]

    df[price_like] = (df[price_like]
                      .replace(0, np.nan)
                      .ffill()
                      .bfill())

    # 8 ▸ calendar reindex (fill holidays/weekends)
    full_idx = pd.date_range(df.index.min(), df.index.max(), freq="D")
    df = df.reindex(full_idx)
    df[price_like] = df[price_like].ffill().bfill()

    # 3 ▸ Prompt Spread
    if "Prompt Spread" not in df.columns and {"%CL 1!", "%CL 2!"}.issubset(df.columns):
        df["Prompt Spread"] = df["%CL 1!"] - df["%CL 2!"]

    # 4 ▸ December colour spreads
    df.reset_index(inplace=True)
    df.rename(columns={"index": "Date (Day)"}, inplace=True)
    df["__YearTmp"] = pd.to_datetime(df["Date (Day)"]).dt.year
    for name, o1, o2 in [("Dec Red", 0, 1),
                         ("Red/Blue", 1, 2),
                         ("Blue/Green", 2, 3)]:
        lhs = [_dec_contract(y + o1) for y in df["__YearTmp"]]
        rhs = [_dec_contract(y + o2) for y in df["__YearTmp"]]

        lut = {c: i for i, c in enumerate(df.columns)}
        lhs_idx = np.array([lut.get(c, -1) for c in lhs])
        rhs_idx = np.array([lut.get(c, -1) for c in rhs])

        mat = df.to_numpy()
        row = np.arange(len(df))
        df[name] = np.where(lhs_idx >= 0, mat[row, lhs_idx], np.nan) - \
                   np.where(rhs_idx >= 0, mat[row, rhs_idx], np.nan)
    df.drop(columns="__YearTmp", inplace=True, errors="ignore")

    return df
