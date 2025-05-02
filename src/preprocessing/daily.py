# ─────────────────────────── src/preprocessing/daily.py ──────────────────────────
"""
Return **daily_df** that already contains

• All %CL outrights (1‑24) and every intra‑curve spread
• Rebuilt **Prompt Spread**  (%CL 1! – %CL 2!) if absent
• December‑colour spreads that roll each 1 Jan
      – Dec Red     = Z(yr)   – Z(yr+1)
      – Red/Blue    = Z(yr+1) – Z(yr+2)
      – Blue/Green  = Z(yr+2) – Z(yr+3)
• For every column in **EIA WEEKLY DATA** (rows 3‑∞, A:P)
      →  <name> (Release)  – value stamped to next Wed, forward‑filled
      →  <name> (Interp)   – Fri‑to‑Fri linear interpolation
• **Cushing Stocks** gets the same Release / Interp treatment, sourced from
  Daily sheet if present, otherwise from the weekly sheet.
• All legacy junk columns are dropped.

Output: tidy DataFrame indexed by calendar day (weekends + holidays filled)."""

from pathlib import Path
import pandas as pd, numpy as np, re
from itertools import combinations

# ── regex helpers --------------------------------------------------------------
_CL_NUM = re.compile(r"%CL (\d+)!")     # %CL 1! … %CL 24!
_Z_CON  = re.compile(r"CL Z\d{2}$")     # CL Z18 … Z28


# ── small utilities ------------------------------------------------------------
def _dec_contract(year: int) -> str:
    return f"CL Z{str(year)[-2:]}"      # 2025 → "CL Z25"

def _next_wed(ts: pd.Timestamp) -> pd.Timestamp:
    off = (2 - ts.weekday() + 7) % 7
    return ts + pd.Timedelta(days=off or 7)


# ── main loader ----------------------------------------------------------------
def load_daily_xlsx(
    xlsx: str | Path,
    daily_sheet: str = "Daily Data",
    weekly_sheet: str = "EIA WEEKLY DATA",
) -> pd.DataFrame:

    # 1 ▸ read Daily sheet (no col limit so new Z contracts are included)
    df = pd.read_excel(
    xlsx, daily_sheet,
    skiprows=5, header=0
        )
    df.columns = df.columns.str.strip()

        # ── NEW — drop %CL legs beyond 12 ────────────────────────────────────
    far_legs = [c for c in df.columns
                    if _CL_NUM.fullmatch(c) and int(_CL_NUM.fullmatch(c).group(1)) > 12]
    if far_legs:
        df.drop(columns=far_legs, inplace=True)

        # drop legacy / helper columns we no longer want
    drop_cols = [c for c in df.columns
                    if c.startswith("Unnamed:")
                    or c in {"Prompt TM", "Filter Range",
                            "CL Settles / Fwd Proj (M1-M2)",
                            "CL Settles / Fwd Proj (M2-M8)"}]
    df.drop(columns=drop_cols, inplace=True, errors="ignore")

    price_cols_raw = [c for c in df.columns if _CL_NUM.fullmatch(c) or _Z_CON.fullmatch(c)]
    df[price_cols_raw] = df[price_cols_raw].apply(
    pd.to_numeric, errors="coerce"
)


    # 2 ▸ build every intra‑curve spread among %CL n!
    cl_cols = [c for c in df.columns if _CL_NUM.fullmatch(c)]
    cl_cols.sort(key=lambda c: int(_CL_NUM.fullmatch(c).group(1)))
    for near, far in combinations(cl_cols, 2):
        df[f"{near} - {far}"] = df[near] - df[far]

    # 3 ▸ rebuild Prompt Spread if workbook removed it
    if "Prompt Spread" not in df.columns and {"%CL 1!", "%CL 2!"} <= set(df.columns):
        df["Prompt Spread"] = df["%CL 1!"] - df["%CL 2!"]

    # 4 ▸ December‑colour spreads (Dec Red, Red/Blue, Blue/Green)
    df["__YearTmp"] = pd.to_datetime(df["Date (Day)"]).dt.year
    for name, o1, o2 in [("Dec Red", 0, 1),
                         ("Red/Blue", 1, 2),
                         ("Blue/Green", 2, 3)]:
        lhs_cols = [_dec_contract(y + o1) for y in df["__YearTmp"]]
        rhs_cols = [_dec_contract(y + o2) for y in df["__YearTmp"]]

        lut = {c: i for i, c in enumerate(df.columns)}
        lhs_idx = np.array([lut.get(c, -1) for c in lhs_cols])
        rhs_idx = np.array([lut.get(c, -1) for c in rhs_cols])

        mat = df.to_numpy()
        row = np.arange(len(df))
        lhs_vals = np.where(lhs_idx >= 0, mat[row, lhs_idx], np.nan)
        rhs_vals = np.where(rhs_idx >= 0, mat[row, rhs_idx], np.nan)
        df[name] = lhs_vals - rhs_vals
    df.drop(columns="__YearTmp", inplace=True, errors="ignore")

    # 5 ▸ index by date
    df["Date (Day)"] = pd.to_datetime(df["Date (Day)"])
    df = df.set_index("Date (Day)").sort_index()

    # ── NEW  ▸ drop rows beyond 'today'  ───────────────────────────────
    today = pd.Timestamp.today().normalize()
    df = df.loc[:today]   

    # 6 ▸ read EIA WEEKLY DATA
    weekly = pd.read_excel(
        xlsx, weekly_sheet,
        skiprows=2, header=0, usecols="A:P"
    )
    weekly.rename(columns={weekly.columns[0]: "Date"}, inplace=True)
    weekly.columns = weekly.columns.str.strip()
    weekly["Date"] = pd.to_datetime(weekly["Date"])
    weekly = weekly.set_index("Date").sort_index()

    def _add_weekly(series: pd.Series, label: str):
        # (a) Release  → next Wed, forward‑fill
        release = series.copy()
        release.index = release.index.map(_next_wed)
        df[f"{label} (Release)"] = release.reindex(df.index).ffill()
        # (b) Interpolated physical path
        interp = (series.reindex(df.index)
                        .interpolate("time")
                        .ffill().bfill())
        df[f"{label} (Interp)"] = interp

    # 6.a ▸ push every weekly metric into daily frame
    for col in weekly.columns:
        _add_weekly(weekly[col].dropna(), col)

    # 6.b ▸ ensure Cushing Release / Interp exist
    if "Cushing Stocks (Mbbl)" in df.columns:
        cush_series = df["Cushing Stocks (Mbbl)"].dropna()
        _add_weekly(cush_series, "Cushing Stocks (Mbbl)")
    else:
        if "Cushing Stocks (Mbbl)" in weekly.columns:
            _add_weekly(weekly["Cushing Stocks (Mbbl)"].dropna(),
                        "Cushing Stocks (Mbbl)")

    # 7 ▸ forward‑fill price‑like columns
    price_like = [c for c in df.columns
                  if _CL_NUM.fullmatch(c)
                  or _Z_CON.fullmatch(c)
                  or " - " in c]
    # 7 ▸ forward‑fill price‑like columns
    df[price_like] = (
        df[price_like]
        .replace(0, np.nan)     # ← NEW: zero → NaN so ffill sees the gap
        .ffill()
        .bfill())

    # 8 ▸ calendar reindex (fill weekends/holidays)
    full_idx = pd.date_range(df.index.min(), df.index.max(), freq="D")
    df = df.reindex(full_idx)
    df[price_like] = df[price_like].ffill().bfill()

    # 9 ▸ tidy return
    df.reset_index(inplace=True)
    df.rename(columns={"index": "Date (Day)"}, inplace=True)
    return df
