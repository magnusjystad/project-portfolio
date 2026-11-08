from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parents[2] / "data"
st.set_page_config(page_title="Backtest", layout="wide")
BT = pd.read_csv(DATA / "backtest_summary.csv", index_col=[0, 1])
E = pd.read_csv(DATA / "exceptions_daily.csv", index_col=0, parse_dates=True)
F = pd.read_csv(DATA / "var_forecasts_daily.csv", index_col=0, parse_dates=True).loc[E.index[0]:]

st.title("VaR backtest, January 2010 – September 2026")
level = st.radio("Confidence level", [99, 95], horizontal=True)
sub = BT.xs(level, level=1)
cols = ["Days", "Exceptions", "Expected", "Rate", "Kupiec p", "Christoffersen p", "Last 250d exceptions", "Max exceptions in 250d"]
if level == 99:
    cols += ["Zone now", "% windows green", "% windows yellow", "% windows red"]
st.dataframe(sub[cols], width="stretch")
st.caption("Kupiec: is the exception rate equal to 1 − confidence? Christoffersen: are exceptions independent from day to day? "
           "p < 0.05 rejects. Basel zones use 99% exceptions in 250 days: green 0–4, yellow 5–9, red 10+.")
model = st.selectbox("Model", ["HS", "EWMA", "MC-t"])
roll = E[f"{model} {level}"].astype(int).rolling(250).sum()
st.subheader(f"{model}: exceptions in the trailing 250 days")
st.line_chart(roll)
st.subheader(f"{model}: daily return vs. −VaR (% of NAV)")
st.line_chart(pd.DataFrame({"Return": F["ret"] * 100, f"−VaR{level}": -F[f"{model} VaR{level}"] * 100}))
