# ── src/preprocessing/daily.py  (full rewritten snippet) ───────────────
from pathlib import Path
import pandas as pd, re
from itertools import combinations
import pandas_market_calendars as mcal

# ----------------------------------------------------------------------
def load_daily_xlsx(xlsx: str | Path,
                    daily_sheet: str = "Daily Data",
                    weekly_eia_sheet: str = "EIA WEEKLY DATA",
                    max_leg: int = 24) -> pd.DataFrame:

    # ---------- 1. read Daily Data (outrights & legacy spreads) -------
    df = pd.read_excel(
        xlsx, daily_sheet,
        skiprows=5, header=0, usecols="B:AI"
    )

    # add December contracts Z18 … Z28  (already present in file)
    # nothing to do – they’re included in B:AI read-range

    # --- build all intra-%CL spreads (same as before) -----------------
    cl_cols = [c for c in df.columns if re.match(r"%CL \d+!", c)]
    cl_cols = sorted(cl_cols, key=lambda c: int(re.search(r"\d+", c).group()))
    for near, far in combinations(cl_cols, 2):
        df[f"{near} - {far}"] = df[near] - df[far]

    # --- drop unwanted legacy cols ------------------------------------
    df.drop(columns={
        "%CL 1! - %CL 2!", "CL Settles / Fwd Proj (M1-M2)",
        "CL Settles / Fwd Proj (M2-M8)", "Filter Range", "Prompt TM"
    }, inplace=True, errors="ignore")

    # ---------- 2. colour spreads  (Dec Red / Red-Blue / Blue-Green) --
    def dec_contract(year: int) -> str:
        return f"CL Z{str(year)[-2:]}"

    z_cols = [c for c in df.columns if re.match(r"CL Z\d{2}$", c)]
    df["Year"] = pd.to_datetime(df["Date (Day)"]).dt.year
    for name, offset1, offset2 in [
        ("Dec Red",    0, 1),
        ("Red/Blue",   1, 2),
        ("Blue/Green", 2, 3)
    ]:
        lhs = [dec_contract(y + offset1) for y in df["Year"]]
        rhs = [dec_contract(y + offset2) for y in df["Year"]]
        df[name] = df.lookup(df.index, lhs) - df.lookup(df.index, rhs)

    # ---------- 3. Cushing Release & Interp  (existing logic) ---------
    df['Date (Day)'] = pd.to_datetime(df['Date (Day)'])
    df = df.set_index('Date (Day)').sort_index()
    cush = df['Cushing Stocks (Mbbl)'].dropna()

    def next_wed(d):                   # helper
        off = (2 - d.weekday() + 7) % 7
        return d + pd.Timedelta(days=off or 7)

    rel_idx = cush.index.map(next_wed)
    cush_release = cush.copy(); cush_release.index = rel_idx
    df['Cushing Stocks (Release)'] = cush_release.reindex(df.index).ffill()
    df['Cushing Stocks (Interp)']  = (
        cush.reindex(df.index).interpolate('time').ffill().bfill()
    )

    # ---------- 4. NEW -- EIA WEEKLY sheet → daily Release/Interp -----
    eia = pd.read_excel(
        xlsx, weekly_eia_sheet,
        skiprows=2, usecols="A:P"
    )
    eia.rename(columns={eia.columns[0]: "Date"}, inplace=True)
    eia["Date"] = pd.to_datetime(eia["Date"])
    eia = eia.set_index("Date").sort_index()

    for col in eia.columns:
        series = eia[col].dropna()

        # (a) Release series
        rel_idx = series.index.map(next_wed)
        s_rel = series.copy(); s_rel.index = rel_idx
        df[f"{col} (Release)"] = s_rel.reindex(df.index).ffill()

        # (b) Interpolated physical series
        s_interp = (
            series.reindex(df.index)
                  .interpolate("time")
                  .ffill().bfill()
        )
        df[f"{col} (Interp)"] = s_interp

    # ---------- 5. re-index to full calendar & forward-fill prices ----
    full_idx = pd.date_range(df.index.min(), df.index.max(), freq='D')
    df = df.reindex(full_idx)

    price_cols = [c for c in df.columns if c.startswith("%CL ") or " - " in c or c.startswith("CL Z")]
    df[price_cols] = df[price_cols].ffill()

    df.reset_index(inplace=True)
    df.rename(columns={"index": "Date (Day)"}, inplace=True)
    return df
