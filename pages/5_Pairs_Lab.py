# pages/5_Pairs_Lab.py
import streamlit as st, pandas as pd
from src.analytics.term_structure import list_legs
from src.analytics.pairs import engle_granger, backtest, batch_scan
from src.viz.pair_resid import resid_chart
from src.viz.pair_equity import equity_chart

st.header("🔗 Pairs Lab")

if "daily_df" not in st.session_state:
    st.warning("Upload workbook first."); st.stop()

df: pd.DataFrame = st.session_state["daily_df"]

# --- universe ----------------------------------------------------------
legs    = list_legs(df)
spreads = [c for c in df.columns if " - " in c or c in ["Prompt Spread", "Dec Red"]]
universe = legs + spreads

# --- pick pair ---------------------------------------------------------
col1, col2 = st.columns(2)
x_sel = col1.selectbox("Series X", universe, index=0)
y_sel = col2.selectbox("Series Y", universe, index=1)

# ----------------------------------------------------------------------
if st.button("Run Cointegration Test"):
    β, p, resid = engle_granger(df, x_sel, y_sel)

    # store in session_state so it persists after rerun
    st.session_state["pair"]   = (x_sel, y_sel)
    st.session_state["β"]      = β
    st.session_state["pval"]   = p
    st.session_state["resid"]  = resid
    st.session_state["bt_result"] = None   # clear old back-test

# ----------------------------------------------------------------------
# display latest cointegration result if exists
if "pair" in st.session_state:
    x_sel, y_sel = st.session_state["pair"]
    β    = st.session_state["β"]
    p    = st.session_state["pval"]
    resid= st.session_state["resid"]

    st.write(f"**Pair:** {x_sel}  vs  {y_sel}")
    st.write(f"**Hedge β:** {β:.3f}")
    st.write(f"**ADF p-value:** {p:.4f}  {'✅ Cointegrated' if p<0.05 else '❌ Not'}")
    st.plotly_chart(resid_chart(resid), use_container_width=True)

    # ----- back-test UI -------------------------------------------------
    with st.expander("Back-test parameters"):
        entry_z  = st.number_input("|z| entry", 1.0, 3.0, 2.0, 0.1)
        exit_z   = st.number_input("|z| exit" , 0.1, 2.0, 0.5, 0.1)
        beta_win = st.slider("β rolling window", 30, 180, 90, 5)

        if st.button("Run back-test"):
            st.session_state["bt_result"] = backtest(
                df, x_sel, y_sel,
                entry_z, exit_z, beta_win
            )

# ----- show back-test result if we have one ---------------------------
bt = st.session_state.get("bt_result")
if bt is not None:
    fig_eq = equity_chart(bt)
    if fig_eq:
        st.plotly_chart(fig_eq, use_container_width=True)
        st.write(f"Total return: **{bt['equity'].iloc[-1]-1:.1%}**")
    else:
        st.info("Back-test produced no equity curve (not enough data).")

st.divider()

# ----- Opportunity scanner -------------------------------------------
with st.expander("📋 Opportunity scanner (z>|2|, p<0.05)"):
    if st.button("Scan universe"):
        scan = batch_scan(df, universe, p_thres=0.05, z_thres=2.0)
        st.dataframe(scan if not scan.empty else pd.DataFrame({"Info":["No pairs found"]}),
                     use_container_width=True, hide_index=True)
