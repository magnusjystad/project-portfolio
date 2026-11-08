"""Northbridge risk dashboard — Streamlit entry page. Run: streamlit run app/Overview.py"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parents[1] / "data"
st.set_page_config(page_title="Northbridge risk dashboard", layout="wide")


@st.cache_data
def load():
    return (json.load(open(DATA / "meta.json")), pd.read_csv(DATA / "policy_weights.csv", index_col=0)["weight"],
            pd.read_csv(DATA / "var_es_asof.csv", index_col=0), pd.read_csv(DATA / "risk_decomposition.csv", index_col=0),
            pd.read_csv(DATA / "stress_historical.csv", index_col=0), pd.read_csv(DATA / "stress_hypothetical.csv", index_col=0))


meta, W, V, DEC, HS, HY = load()
nav = meta["nav"]
st.title("Northbridge University Endowment — risk overview")
st.caption(f"Fictional $2.0bn portfolio at the Project 5 strategic allocation · risk as of {meta['asof']} · "
           "data: yfinance adjusted closes, ishares.com")
c = st.columns(4)
c[0].metric("Net asset value", f"${nav / 1e9:.1f}bn")
c[1].metric(f"1-day 99% VaR (historical) · {V.loc['HS VaR99', '% of NAV']:.2%} of NAV", f"${V.loc['HS VaR99', '$m']:.1f}m")
c[2].metric(f"1-day 97.5% ES (historical) · {V.loc['HS ES97.5', '% of NAV']:.2%} of NAV", f"${V.loc['HS ES97.5', '$m']:.1f}m")
c[3].metric("EWMA volatility (annualized)", f"{meta['ewma_vol_ann_next']:.1%}")

left, right = st.columns(2)
with left:
    st.subheader("Strategic weights")
    st.bar_chart(W[W > 0].rename("Weight"))
with right:
    st.subheader("Contribution to volatility (EWMA)")
    st.bar_chart(DEC[["Weight", "% of volatility"]], stack=False)
st.subheader("Worst stress outcomes")
st.dataframe(pd.concat([HS[["Portfolio", "Loss $m"]], HY[["Portfolio", "Loss $m"]]])
             .style.format({"Portfolio": "{:.1%}", "Loss $m": "{:,.0f}"}), width="stretch")
