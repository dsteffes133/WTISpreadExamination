import streamlit as st, pandas as pd
from src.alerts.engine import (
    check_prompt_shock, check_dec_red, check_vol_spike,
    check_spread_hi_lo, check_curve_kink, alert_bar
)
from src.viz.alert_plots import plot_alert_ts  # small helper to convert ts→figure

st.header("🚨 Alerts Center")

df: pd.DataFrame = st.session_state["daily_df"]

alerts = {
    "Prompt": check_prompt_shock(df),
    "DecRed": check_dec_red(df),
    "Vol":    check_vol_spike(df),
    "Hi/Lo":  check_spread_hi_lo(df, "%CL 1!", "%CL 2!"),
    "Kink":   check_curve_kink(df),
}

alert_bar(alerts)
st.divider()

# expandable cards
for name, data in alerts.items():
    with st.expander(f"{name} details", expanded=data is not None):
        if data:
            st.plotly_chart(plot_alert_ts(name, data["ts"]), use_container_width=True)
            hist = st.session_state.setdefault(f"{name}_hist", [])
            if not hist or hist[-1]["date"] != df["Date (Day)"].iloc[-1]:
                hist.append({"date": df['Date (Day)'].iloc[-1], "msg": data["msg"]})
            st.table(pd.DataFrame(hist).tail(10))
        else:
            st.write("No anomaly in selected window.")
