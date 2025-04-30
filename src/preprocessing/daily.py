from pathlib import Path
from typing import Union, IO

import pandas as pd
import numpy as np
import re
from itertools import combinations
import pandas_market_calendars as mcal


# ──────────────────────────────────────────────────────────────────────
MONTH_RE = re.compile(r"%CL\s+(\d+)!")        # captures month leg as int


def _is_leg(col: str) -> bool:
    return bool(MONTH_RE.fullmatch(col))


def _leg_num(col: str) -> int:
    return int(MONTH_RE.fullmatch(col).group(1))


# ──────────────────────────────────────────────────────────────────────
def load_daily_xlsx(
    xlsx: Union[str, Path, IO[bytes]],
    sheet: str = "Daily Data"
) -> pd.DataFrame:
    """
    Read *Daily Data* sheet, build spreads, clean, fill forward.

    Returns
    -------
    pd.DataFrame
        Cleaned daily data with **'Date (Day)'** as a column (not index),
        no NaNs, outrights/spreads only up to CL12, plus engineered
        Cushing release/interpolation columns.
    """
    # ------------------------------------------------------------------
    df = pd.read_excel(xlsx, sheet, skiprows=5, header=0, usecols="B:AI")

    # 1) Build calendar-spread columns
    cl_cols = sorted([c for c in df.columns if _is_leg(c)], key=_leg_num)

    for near, far in combinations(cl_cols, 2):
        df[f"{near} - {far}"] = df[near] - df[far]

    # 2) Drop hard-coded throw-away columns
    df = df.drop(
        columns={
            "%CL 1! - %CL 2!",
            "CL Settles / Fwd Proj (M1-M2)",
            "CL Settles / Fwd Proj (M2-M8)",
            "Filter Range",
            "Prompt TM",
        },
        errors="ignore",
    )

    # 3) Prompt & Dec-Red extras
    df["Prompt Spread"] = df["%CL 1!"] - df["%CL 2!"]
    df["Dec Red"] = df["CL Z25"] - df["CL Z26"]

    # 4) Drop legs/spreads beyond 12 months
    meta_cols = {
        "Date (Day)",
        "Cushing Stocks (Mbbl)",
        "Prompt Spread",
        "Dec Red",
    }
    drop_cols = [
    c
    for c in df.columns
    if c not in meta_cols
    and any(int(x) > 12 for x in MONTH_RE.findall(c))    # ← fixed
]
    df = df.drop(columns=drop_cols)

    # 5) Date handling & sort
    df["Date (Day)"] = pd.to_datetime(df["Date (Day)"])
    df = df.set_index("Date (Day)").sort_index()

    # 6) Cushing inventory engineering
    cush = df["Cushing Stocks (Mbbl)"].dropna()

    def _next_wed(d):  # first Wed *after* d
        off = (2 - d.weekday() + 7) % 7 or 7
        return d + pd.Timedelta(days=off)

    cush_release = cush.copy()
    cush_release.index = cush.index.map(_next_wed)
    df["Cushing Stocks (Release)"] = cush_release.reindex(df.index).ffill()

    cush_interp = (
        cush.reindex(df.index)
        .interpolate(method="time")
        .ffill()
        .bfill()
    )
    df["Cushing Stocks (Interp)"] = cush_interp
    df["Delta Cushing Release"] = df["Cushing Stocks (Release)"].diff()
    df["Delta Cushing Interp"] = df["Cushing Stocks (Interp)"].diff()

    # 7) Zero-value row filter & full calendar re-index
    df = df[df["%CL 1!"] != 0]
    full_idx = pd.date_range(df.index.min(), df.index.max(), freq="D")
    df = df.reindex(full_idx)

    price_cols = df.columns.difference(
        ["Prompt TM", "Cushing Stocks (Mbbl)"]
    )
    df[price_cols] = df[price_cols].ffill()
    df["Cushing Stocks (Mbbl)"] = df["Cushing Stocks (Mbbl)"].ffill()

    today = pd.Timestamp("today").normalize()      # e.g. 2025-04-29 00:00:00
    df = df.loc[df.index <= today]

    # 8) Return with date restored as column
    return df.reset_index(names="Date (Day)")
