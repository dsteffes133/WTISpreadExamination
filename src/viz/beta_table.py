import streamlit as st
import pandas as pd

def beta_ranking(beta_df: pd.DataFrame, top: int = 10):
    """Show table of top |β| spreads with stats."""
    tbl = (
        beta_df.reindex(beta_df["beta"].abs().sort_values(ascending=False).index)
                .head(top)
                .reset_index(names="Instrument")
                .assign(beta=lambda d: d["beta"].round(3),
                        t_stat=lambda d: d["t_stat"].round(2),
                        r2=lambda d: d["r2"].round(2))
    )
    st.dataframe(tbl, use_container_width=True, hide_index=True)
