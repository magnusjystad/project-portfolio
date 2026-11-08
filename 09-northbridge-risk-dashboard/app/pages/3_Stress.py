import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.risk import bond_return  # noqa: E402

DATA = ROOT / "data"
st.set_page_config(page_title="Stress", layout="wide")
W = pd.read_csv(DATA / "policy_weights.csv", index_col=0)["weight"]
HS = pd.read_csv(DATA / "stress_historical.csv", index_col=0)
HY = pd.read_csv(DATA / "stress_hypothetical.csv", index_col=0)
ish = pd.read_csv(DATA / "ishares_bond_characteristics.csv", index_col=0)
NAV = 2.0e9

st.title("Stress tests")
st.subheader("Historical windows replayed on today's weights")
st.dataframe(HS.style.format({c: "{:.1%}" for c in HS.columns if c not in ("Start", "End", "Loss $m")} | {"Loss $m": "{:,.0f}"}),
             width="stretch")
st.subheader("Hypothetical scenarios")
st.dataframe(HY.style.format({c: "{:.1%}" for c in HY.columns if c != "Loss $m"} | {"Loss $m": "{:,.0f}"}),
             width="stretch")

st.subheader("Build your own scenario")
c = st.columns(5)
eq = c[0].slider("Equities & REITs (%)", -50, 30, -30) / 100
dy = c[1].slider("Treasury yields (bp)", -300, 300, -100) / 1e4
ds = c[2].slider("Credit spreads (bp)", -200, 600, 250) / 1e4
gold = c[3].slider("Gold (%)", -40, 40, 0) / 100
cmd = c[4].slider("Commodities (%)", -50, 50, 0) / 100
dur, cvx = ish["Effective duration (yrs)"].astype(float), ish["Convexity (/100)"].astype(float)
r = pd.Series(0.0, W.index)
for t in ["SPY", "EFA", "EEM", "VNQ"]:
    r[t] = eq
for t in ["IEF", "TLT", "TIP"]:
    r[t] = bond_return(dur[t], cvx[t], dy)
for t in ["LQD", "HYG"]:
    r[t] = bond_return(dur[t], cvx[t], dy, spread_dur=dur[t], ds=ds)
r["GLD"], r["DBC"] = gold, cmd
port = float(r @ W)
st.metric(f"Portfolio P&L: {'−' if port < 0 else '+'}${abs(port) * NAV / 1e6:,.0f}m", f"{port:.1%}")
st.dataframe(pd.DataFrame({"Weight": W, "Shocked return": r, "Contribution": W * r})[W > 0]
             .style.format("{:.2%}"), width="stretch")
st.caption("Bond ETFs revalued with effective duration and convexity from ishares.com (as of the dates in "
           "data/ishares_bond_characteristics.csv). Spread duration is set equal to effective duration.")
