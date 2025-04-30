import streamlit as st
import pandas as pd

def show_leaderboard(df: pd.DataFrame, threshold: float = 2.0):
    """Display top-mover table; highlight whole row if |z| exceeds threshold."""
    def highlight(row):
        if abs(row["z-score"]) > threshold:
            return ['background-color:#ffdddd'] * len(row)
        return [''] * len(row)

    styled = (
        df.style
          .apply(highlight, axis=1)
          .format({"Δ price ($/bbl)": "{:+.2f}", "z-score": "{:+.2f}"})
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)