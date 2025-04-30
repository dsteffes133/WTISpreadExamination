from pathlib import Path
from typing import Union, IO

import pandas as pd
import re
from itertools import combinations


MONTH_RE = re.compile(r"%CL\s+(\d+)!")


def _is_leg(col: str) -> bool:
    return bool(MONTH_RE.fullmatch(col))


def _leg_num(col: str) -> int:
    return int(MONTH_RE.fullmatch(col).group(1))


def load_weekly_xlsx(
    xlsx: Union[str, Path, IO[bytes]],
    sheet: str = "Weekly Data"
) -> pd.DataFrame:
    """
    Read *Weekly Data* sheet, build spreads, clean, forward-fill per column.

    Returns
    -------
    pd.DataFrame
        Cleaned weekly data with **'Date (Week)'** column (not index),
        no NaNs, outrights/spreads only up to CL12.
    """
    df = pd.read_excel(xlsx, sheet, skiprows=5, header=0, usecols="B:AH")

    # 1) Spread generation
    cl_cols = sorted([c for c in df.columns if _is_leg(c)], key=_leg_num)
    for near, far in combinations(cl_cols, 2):
        df[f"{near} - {far}"] = df[near] - df[far]

    # 2) Drops & prompt/Dec-Red
    df = df.drop(
        columns={
            "SBM Stocks (Mbbl)",
            "%CL 1! - %CL 2!",
            "CL Settles / Fwd Proj (M1-M2)",
            "CL Settles / Fwd Proj (M2-M8)",
            "Filter Range",
            "Prompt TM",
        },
        errors="ignore",
    )
    df["Prompt Spread"] = df["%CL 1!"] - df["%CL 2!"]
    df["Dec Red"] = df["CL Z25"] - df["CL Z26"]

    # 3) 12-month filter
    meta_cols = {"Date (Week)", "Cushing Stocks (Mbbl)", "Prompt Spread", "Dec Red"}
    drop_cols = [
    c
    for c in df.columns
    if c not in meta_cols
    and any(int(x) > 12 for x in MONTH_RE.findall(c))    # ← fixed
]
    df = df.drop(columns=drop_cols)

    # 4) Forward-fill by column
    df["Date (Week)"] = pd.to_datetime(df["Date (Week)"])
    df = df.sort_values("Date (Week)")
    fill_cols = df.columns.difference(["Date (Week)"])
    df[fill_cols] = df[fill_cols].ffill()

    df.reset_index(drop=True, inplace=True)

    today = pd.Timestamp("today").normalize()
    df = df[df["Date (Week)"] <= today]

    return df


