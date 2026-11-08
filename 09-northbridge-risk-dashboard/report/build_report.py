"""Builds the 2-page monthly risk report (report/risk_report.pdf), as of 30 September 2026."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import pandas as pd

from common.report import Report

D, F = ROOT / "data", ROOT / "report" / "figures"
m = json.load(open(D / "meta.json"))
W = pd.read_csv(D / "policy_weights.csv", index_col=0)["weight"]
V = pd.read_csv(D / "var_es_asof.csv", index_col=0)
T = pd.read_csv(D / "var_10day.csv", index_col=0)
BT = pd.read_csv(D / "backtest_summary.csv", index_col=[0, 1])
DEC = pd.read_csv(D / "risk_decomposition.csv", index_col=0)
HS = pd.read_csv(D / "stress_historical.csv", index_col=0)
HY = pd.read_csv(D / "stress_hypothetical.csv", index_col=0)
ish = pd.read_csv(D / "ishares_bond_characteristics.csv", index_col=0)
pct = lambda x, d=2: f"{x * 100:.{d}f}%"
usd = lambda x: f"${x:,.1f}m"
b99 = BT.xs(99, level=1)
best = (b99["Exceptions"] - b99["Expected"]).abs().idxmin()
worst_hist = HS["Portfolio"].astype(float).idxmin()

r = Report(ROOT / "report" / "risk_report.pdf", "Northbridge University Endowment — Monthly Risk Report",
           f"For the Investment Committee · As of 30 September 2026 · NAV $2.0bn (fictional) · Strategic allocation: "
           + ", ".join(f"{t} {w:.0%}" for t, w in W[W > 0].items()))
r.h2("Key messages")
r.bullets([
    f"One-day 99% VaR is {usd(V.loc['HS VaR99','$m'])} ({pct(V.loc['HS VaR99','% of NAV'])} of NAV) on historical simulation, "
    f"the model that has been best calibrated since 2010 ({int(b99.loc['HS','Exceptions'])} exceptions vs. "
    f"{b99.loc['HS','Expected']:.0f} expected). Expected Shortfall at 97.5% is {usd(V.loc['HS ES97.5','$m'])}.",
    f"Current EWMA volatility is {pct(m['ewma_vol_ann_next'],1)} a year, below the {pct(m['realised_vol_full'],1)} realised since 2007: "
    f"markets are calm, so the EWMA model currently shows the lowest 99% VaR. Its forecasts rise fastest when volatility returns.",
    f"REITs (VNQ) and emerging markets (EEM) are {pct(W['VNQ']+W['EEM'],0)} of the portfolio and "
    f"{pct(DEC.loc['VNQ','% of volatility'] + DEC.loc['EEM','% of volatility'],0)} of its volatility.",
    f"The worst historical stress, the {worst_hist.lower()}, would cost {pct(-HS.loc[worst_hist,'Portfolio'],1)} "
    f"(${-HS.loc[worst_hist,'Loss $m']:,.0f}m) on today's weights; the hypothetical recession costs "
    f"{pct(-HY.loc['Recession','Portfolio'],1)} (${-HY.loc['Recession','Loss $m']:,.0f}m).",
    f"Backtest: the EWMA-normal model failed Kupiec's test ({int(b99.loc['EWMA','Exceptions'])} exceptions vs. "
    f"{b99.loc['EWMA','Expected']:.0f}) and is in the Basel {b99.loc['EWMA','Zone now'].lower()} zone today. All three models "
    f"fail Christoffersen's independence test: exceptions cluster in stress periods.",
])
r.h2("1. Value-at-Risk and Expected Shortfall (1 day)")
vt = pd.DataFrame({mm: {"VaR 95%": f"{usd(V.loc[f'{mm} VaR95','$m'])} ({pct(V.loc[f'{mm} VaR95','% of NAV'])})",
                        "VaR 99%": f"{usd(V.loc[f'{mm} VaR99','$m'])} ({pct(V.loc[f'{mm} VaR99','% of NAV'])})",
                        "ES 97.5%": f"{usd(V.loc[f'{mm} ES97.5','$m'])} ({pct(V.loc[f'{mm} ES97.5','% of NAV'])})",
                        "10-day VaR 99%, √10": pct(T.loc[f'{mm} VaR99', '1-day VaR x sqrt(10)'])}
                   for mm in ["HS", "EWMA", "MC-t"]}).T
vt.index = ["Historical simulation (500 days)", "Parametric EWMA (λ = 0.94)", "Monte Carlo Student-t (ν = 5)"]
vt.index.name = "Model"
r.table(vt, caption=f"Overlapping 10-day historical returns give a 99% 10-day VaR of "
        f"{pct(T.iloc[1]['Overlapping 10-day HS (last 500 days)'])} over the last 500 days and "
        f"{pct(T.iloc[1]['Overlapping 10-day HS (full sample)'])} over the full sample since 2007; √10 scaling sits between the two.",
        font=7.5)
dt = pd.DataFrame({"Weight": DEC["Weight"].map(lambda x: f"{x:.0%}"),
                   "Component VaR 99%": DEC["Component VaR99 ($m)"].map(usd),
                   "Share of volatility": DEC["% of volatility"].map(lambda x: pct(x, 1)),
                   "Stand-alone vol.": DEC["Stand-alone vol (ann.)"].map(lambda x: pct(x, 1))})
dt.index.name = "ETF"
r.h2("2. Risk decomposition (EWMA covariance)")
r.table(dt, caption=f"Component VaRs add up to the EWMA 99% VaR for 1 October 2026 ({pct(m['ewma_var99_next'])}). Gold's "
        "stand-alone volatility is the highest in the portfolio after its recent rally.", font=7.5)
r.h2("3. Backtest of 99% VaR, January 2010 – September 2026")
bt = pd.DataFrame({"Exceptions / expected": [f"{int(b99.loc[k,'Exceptions'])} / {b99.loc[k,'Expected']:.1f}" for k in b99.index],
                   "Kupiec p": b99["Kupiec p"].map(lambda x: f"{x:.3f}").values,
                   "Christoffersen p": b99["Christoffersen p"].map(lambda x: f"{x:.3f}").values,
                   "Basel zone now (last 250 days)": [f"{z} ({int(n)})" for z, n in zip(b99["Zone now"], b99["Last 250d exceptions"])],
                   "Windows green / yellow / red": [f"{g:.0%} / {y:.0%} / {rr:.0%}" for g, y, rr in
                                                    zip(b99["% windows green"], b99["% windows yellow"], b99["% windows red"])]},
                  index=["Historical simulation", "Parametric EWMA", "Monte Carlo Student-t"])
bt.index.name = "Model"
r.table(bt, caption=f"{m['bt_days']:,} trading days. p < 0.05 rejects correct coverage (Kupiec) or independence (Christoffersen).",
        font=7.5)
r.image(F / "fig_backtest.png", 15.5)
r.h2("4. Stress tests on today's weights")
st = pd.concat([HS[["Portfolio", "Loss $m"]].assign(Type="Historical", Window=HS["Start"] + " to " + HS["End"]),
                HY[["Portfolio", "Loss $m"]].assign(Type="Hypothetical",
                                                    Window=["Equities −30%, yields −100 bp, spreads +250 bp",
                                                            "Equities −20%, yields +150 bp, commodities +25%, gold +15%"])])
stt = pd.DataFrame({"Type": st["Type"], "Window / shock": st["Window"],
                    "Portfolio": st["Portfolio"].astype(float).map(lambda x: pct(x, 1)),
                    "P&amp;L": st["Loss $m"].astype(float).map(lambda x: f"−${-x:,.0f}m")})
stt.index.name = "Scenario"
r.table(stt, caption=f"Historical: buy-and-hold ETF total returns between the closes on the start and end dates. Hypothetical: "
        f"TLT revalued with effective duration {ish.loc['TLT','Effective duration (yrs)']} years and convexity "
        f"{ish.loc['TLT','Convexity (/100)']}, HYG with duration {ish.loc['HYG','Effective duration (yrs)']} years, used as both "
        f"rate and spread duration (ishares.com, as of {ish.loc['TLT','Effective duration (yrs) as of']} and "
        f"{ish.loc['HYG','Effective duration (yrs) as of']}).", font=7.5)
print("pages:", r.build())
