import streamlit as st  
from datetime import datetime
import pandas as pd, numpy as np
from src.analytics.spread_summary import compute_spread
from src.analytics.rolling_vol import rolling_vol
from src.analytics.term_structure import list_legs

def _z(series, win):                      # helper
    return (series - series.rolling(win).mean())/series.rolling(win).std()

def check_prompt_shock(df):
    s = compute_spread(df, "%CL 1!", "%CL 2!").dropna()
    move = s.diff().iloc[-1]
    sig  = s.diff().rolling(30).std().iloc[-2]
    if abs(move) > 0.40 and abs(move) > 2*sig:
        return dict(ts=s[-60:], msg=f"Δ {move:+.2f} (>2σ)")
    return None

def check_dec_red(df):
    s = df["CL Z25"] - df["CL Z26"]
    z = _z(s, 252*5)
    if abs(z.iloc[-1]) > 2.5:
        return dict(ts=z[-750:], msg=f"z={z.iloc[-1]:+.2f}")
    return None

def check_vol_spike(df) -> dict | None:
    """
    Detect 1‑day vol jump: today’s σ > 3 × yesterday’s.
    Returns None if:
      • %CL 1! column missing
      • fewer than TWO non‑NaN σ observations
    """
    if "%CL 1!" not in df.columns:
        return None

    vol = rolling_vol(
        df, ["%CL 1!"],
        window=20,          # 20‑day look‑back
        annualize=False,
        min_periods=2       # start as soon as we have 2 returns
    )["%CL 1!"].dropna()

    # need at least TWO valid rows
    if len(vol) < 2:
        return None

    today, prev = vol.iloc[-1], vol.iloc[-2]
    if pd.notna(today) and pd.notna(prev) and today > 3 * prev:
        return dict(ts=vol.tail(200), msg=f"σ jump: {today:.3f}")
    return None

def check_spread_hi_lo(df, near, far, lookback=504):
    s = compute_spread(df, near, far).tail(lookback)
    if s.iloc[-1] == s.max():
        return dict(ts=s, msg="‼ New 2-yr high")
    if s.iloc[-1] == s.min():
        return dict(ts=s, msg="‼ New 2-yr low")
    return None

def check_curve_kink(df):
    legs = list_legs(df, 12)
    today = df.set_index("Date (Day)").iloc[-1][legs]
    prev  = df.set_index("Date (Day)").iloc[-2][legs]
    diff  = today - prev
    sig   = df.set_index("Date (Day)")[legs].diff().rolling(60).std().iloc[-2]
    for i in range(1, len(legs)-1):
        if abs(diff[i]) > 2*sig[i] and abs(diff[i-1]) < 1*sig[i-1] and abs(diff[i+1]) < 1*sig[i+1]:
            return dict(ts=diff, msg=f"Kink at M{i+1}: {diff[i]:+.2f}")
    return None

def alert_bar(alerts):
    cols = st.columns(len(alerts))
    for (name, data), col in zip(alerts.items(), cols):
        if data is None:
            col.markdown(f"<div style='background:#28a745;border-radius:4px;text-align:center;'> {name} ✅ </div>", unsafe_allow_html=True)
        else:
            col.markdown(f"<div style='background:#d9534f;border-radius:4px;text-align:center;'> {name} ⚠️ </div>", unsafe_allow_html=True)
            col.caption(data['msg'])
