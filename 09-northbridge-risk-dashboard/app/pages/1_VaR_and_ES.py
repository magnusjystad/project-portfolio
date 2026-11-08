import json
from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parents[2] / "data"
st.set_page_config(page_title="VaR & ES", layout="wide")
meta = json.load(open(DATA / "meta.json"))
V = pd.read_csv(DATA / "var_es_asof.csv", index_col=0)
T = pd.read_csv(DATA / "var_10day.csv", index_col=0)
F = pd.read_csv(DATA / "var_forecasts_daily.csv", index_col=0, parse_dates=True)
DEC = pd.read_csv(DATA / "risk_decomposition.csv", index_col=0)

st.title("Value-at-Risk and Expected Shortfall")
st.caption(f"1-day horizon, as of {meta['asof']}. HS = historical simulation (500 days); EWMA = parametric normal with "
           "RiskMetrics λ = 0.94; MC-t = 10,000 draws from a multivariate Student-t with 5 degrees of freedom.")
tab = pd.DataFrame({m: {"VaR 95%": V.loc[f"{m} VaR95", "$m"], "VaR 99%": V.loc[f"{m} VaR99", "$m"],
                        "ES 97.5%": V.loc[f"{m} ES97.5", "$m"]} for m in ["HS", "EWMA", "MC-t"]}).T
st.subheader("Current estimates ($m)")
st.dataframe(tab.style.format("{:.1f}"), width="stretch")

st.subheader("History of the 99% VaR forecasts (% of NAV)")
start = st.slider("From year", 2009, 2026, 2019)
st.line_chart(F.loc[str(start):, ["HS VaR99", "EWMA VaR99", "MC-t VaR99"]] * 100)

st.subheader("10-day VaR (% of NAV)")
st.dataframe((T * 100).style.format("{:.2f}"), width="stretch")
st.subheader("Component VaR (99%, EWMA)")
st.dataframe(DEC.style.format({"Weight": "{:.0%}", "Component VaR99 (% NAV)": "{:.3%}", "Component VaR99 ($m)": "{:.1f}",
                               "% of volatility": "{:.1%}", "Stand-alone vol (ann.)": "{:.1%}"}), width="stretch")
