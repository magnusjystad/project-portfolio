"""Bond portfolio scenario tool. Run: streamlit run app/scenario_tool.py"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from yieldcurve import bonds as B, curve as C, scenarios as S  # noqa: E402

st.set_page_config(page_title="Treasury scenario tool", layout="wide")


@st.cache_data
def load_par():
    return pd.read_csv(ROOT / "data" / "treasury_par_yields_daily.csv", index_col=0, parse_dates=True)


par_all = load_par()
st.title("US Treasury curve scenario tool")
dates = par_all.loc["2006":].index
date = st.sidebar.date_input("Curve date", value=pd.Timestamp("2026-09-30"), min_value=dates[0].date(),
                             max_value=dates[-1].date())
d = par_all.index[par_all.index <= pd.Timestamp(date)][-1]
zc = C.ZeroCurve(C.par_points(par_all.loc[d]))
st.caption(f"Zero curve bootstrapped from U.S. Treasury par yields on {d:%d %B %Y} (cubic spline, semiannual grid). "
           "Shifts are applied to continuously compounded zero rates; bonds are fully revalued.")

preset = st.sidebar.selectbox("Preset", ["Custom"] + list(S.SCENARIOS))
defaults = (0, 0, 0, 0) if preset == "Custom" else tuple(round(float(S.SCENARIOS[preset](np.array([m]))[0]) * 1e4, 2)
                                                        for m in (2, 5, 10, 30))
st.sidebar.markdown("**Zero-rate shift at each key maturity (bp)** — linear in between, flat outside")
k = [st.sidebar.slider(f"{m}y", -300.0, 300.0, float(v), 5.0, key=f"{preset}{m}") for m, v in zip([2, 5, 10, 30], defaults)]
shift = lambda t: np.interp(np.asarray(t, float), [2, 5, 10, 30], np.array(k) / 1e4)

b7, b2, b30 = B.par_bond(zc, 7), B.par_bond(zc, 2), B.par_bond(zc, 30)
D = lambda b: b.mod_duration_convexity(b.coupon)[0]
w30 = (D(b7) - D(b2)) / (D(b30) - D(b2))
N = 100e6
ports = {"Bullet (7y)": B.Portfolio([b7], [N]), "Barbell (2y/30y)": B.Portfolio([b2, b30], [N * (1 - w30), N * w30]),
         "Ladder (1–10y)": B.Portfolio([B.par_bond(zc, m) for m in range(1, 11)], [N / 10] * 10)}
rows = {}
for name, p in ports.items():
    r = S.portfolio_pnl(p, zc, shift)
    rows[name] = {**{f"{m} ($m)": v / 1e6 for m, v in r.items()}, "Modified duration": p.mod_duration(zc),
                  **S.key_rate_durations(p, zc), **{f"12m {kk}": vv for kk, vv in S.horizon_return(p, zc).items()}}
T = pd.DataFrame(rows).T
c1, c2 = st.columns([1.1, 1])
with c1:
    st.subheader("Scenario P&L on $100m")
    st.dataframe(T[[c for c in T.columns if "$m" in c]].style.format("{:+.2f}"), width="stretch")
    st.subheader("Risk and 12-month carry / roll-down (curve unchanged)")
    st.dataframe(T[[c for c in T.columns if "$m" not in c]].style.format("{:.3f}"), width="stretch")
with c2:
    st.subheader("Zero curve before and after")
    t = np.linspace(0.5, 30, 60)
    st.line_chart(pd.DataFrame({"Before": zc.zero_cc(t) * 100, "After": (zc.zero_cc(t) + shift(t)) * 100},
                               index=pd.Index(t, name="Maturity (years)")))
