"""Builds the Investment Policy Statement (report/ips.pdf) from the notebook outputs."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import pandas as pd

from common.report import Report

D, F = ROOT / "data", ROOT / "report" / "figures"
W = pd.read_csv(D / "candidate_weights.csv", index_col=0)
ST = pd.read_csv(D / "candidate_stats.csv", index_col=0)
A = pd.read_csv(D / "ltcma2026_usd_assumptions.csv", index_col=0)
H = pd.read_csv(D / "ltcma_vs_history.csv", index_col=0)
SENS = pd.read_csv(D / "sensitivity_reit_assumption.csv", index_col=0)
m = json.load(open(D / "meta.json"))
C = m["chosen"]
w = pd.read_csv(D / "final_policy_weights.csv", index_col=0)["weight"]
PS = pd.read_csv(D / "final_policy_stats.csv", index_col=0).iloc[:, 0]
pct = lambda x, d=1: f"{x * 100:.{d}f}%"
NAMES = {"SPY": "US large-cap equities", "EFA": "Developed ex-US equities", "EEM": "Emerging market equities",
         "IEF": "US Treasuries 7-10y", "TLT": "US Treasuries 20y+", "TIP": "US inflation-linked bonds",
         "LQD": "US investment-grade corporates", "HYG": "US high yield", "VNQ": "US REITs", "GLD": "Gold",
         "DBC": "Broad commodities"}
s = PS

r = Report(ROOT / "report" / "ips.pdf", "Northbridge University Endowment: Investment Policy Statement",
           "Prepared by the investment consultant for the Investment Committee · Proposed for adoption · "
           "Capital market assumptions as of 30 September 2025 · Fictional client")

r.h1("1. Purpose")
r.p("This Investment Policy Statement (IPS) sets out how the assets of the Northbridge University Endowment "
    "(the Endowment) are invested. It defines the Endowment's objectives and constraints, the strategic asset "
    "allocation that the Investment Committee (the Committee) has adopted to meet them, the permitted ranges "
    "around that allocation, the policy benchmark against which results are measured, and how the portfolio "
    "is rebalanced, monitored and reviewed. It is written to give continuity across changes in Committee "
    "membership and staff, and to protect the Endowment from decisions made under short-term market pressure.")
r.p("The Endowment has $2.0 billion of assets and a perpetual horizon. It supports the University's operating "
    "budget through an annual distribution. Its central financial goal is <b>intergenerational equity</b>: "
    "future students and faculty should receive at least the same real support as current ones, which requires "
    "the Endowment to preserve the purchasing power of its assets after spending and costs.")

r.h1("2. Governance and roles")
r.bullets([
    "<b>Board of Trustees:</b> approves this IPS and the spending rule; appoints the Committee; receives an annual report.",
    "<b>Investment Committee:</b> meets quarterly; approves the strategic allocation, ranges and benchmark; "
    "appoints and dismisses the consultant and investment vehicles; reviews performance and risk each quarter; "
    "conducts the annual review in Section 9. Changes to the strategic allocation require a Committee vote.",
    "<b>Investment staff (CIO office):</b> implements the policy within the ranges; executes rebalancing under "
    "Section 7 without further approval; reports breaches to the Committee chair within two business days.",
    "<b>Investment consultant:</b> provides capital market assumptions, asset-liability and allocation analysis, "
    "performance and risk reporting, and independent advice. The consultant is a fiduciary for its advice.",
    "<b>Custodian:</b> holds the assets, provides independent valuations and transaction records.",
])

r.h1("3. Objectives")
r.bullets([
    f"<b>Return objective:</b> a long-term net total return of US inflation + 4.9% a year, which covers spending "
    f"(4.5%) and costs (0.40%) and so preserves real value. Using the J.P. Morgan 2026 inflation assumption of "
    f"{pct(m['inflation'])}, the nominal hurdle is {pct(m['objective'])} a year (compound).",
    "<b>Spending rule:</b> each year the Endowment distributes 4.5% of the average market value of the trailing "
    "12 quarter-ends. Averaging smooths the budget: a 20% market fall reduces spending gradually over three years.",
    "<b>Costs:</b> all-in investment costs of 0.40% a year, monitored annually.",
    "<b>Risk limit:</b> expected volatility no higher than 12% a year, and no more than a 5% probability of a "
    "one-year loss worse than −20%, both measured on the consultant's capital market assumptions.",
])

r.h1("4. Constraints")
r.bullets([
    "<b>Liquidity and mandate:</b> liquid assets only. The Endowment invests through 11 US-listed ETFs (Section 5) "
    "and holds no private assets, so it can meet spending and rebalance at any time.",
    "<b>Concentration:</b> no more than 40% in any one ETF.",
    "<b>Asset-class limits:</b> equities (SPY, EFA, EEM, VNQ) 40–70%; Treasuries and TIPS (IEF, TLT, TIP) at least "
    "15%; gold and commodities (GLD, DBC) at most 10%. These limits apply to the strategic (target) allocation; "
    "Section 7 explains how they interact with rebalancing.",
    "<b>Leverage and derivatives:</b> none. No short positions.",
    "<b>Time horizon:</b> perpetual; the Committee evaluates the policy over rolling 10-year periods.",
    "<b>Tax and legal:</b> the Endowment is a tax-exempt US educational endowment governed by UPMIFA "
    "(the Uniform Prudent Management of Institutional Funds Act), which requires prudent, diversified investing "
    "in light of the institution's needs.",
])

r.h1("5. Strategic asset allocation and ranges")
r.p(f"The Committee adopts the <b>{C}</b> portfolio. It was chosen from three candidates on the constrained efficient "
    f"frontier (Conservative 8%, Balanced 10% and Growth 12% expected volatility), using the rule set in advance: "
    f"the candidate with the highest probability of preserving real value over 20 years that also meets the risk "
    f"limit. All three candidates met the risk limit, and {C} had the highest probability "
    f"({pct(ST.loc[C, 'P(real value preserved, 20y)'])}). Appendix A summarises the analysis.")
r.p(f"For implementation the frontier weights ({', '.join(f'{t} {pct(W.loc[t, C])}' for t in W.index if W.loc[t, C] > 0)}) "
    f"are rounded to whole percentages. Of the roundings that sum to 100% and meet every limit, the one with the highest "
    f"expected return is adopted. Rounding EEM up to 20% would have lifted expected volatility to just above 12%, so EEM "
    f"is 19% and HYG 16%. The rounded policy keeps a {pct(s['P(real value preserved, 20y)'])} probability of preserving real value.")
rng = pd.DataFrame({"Asset class": [NAMES[t] for t in W.index], "Target": w.map(pct),
                    "Lower": (w * 0.8).map(pct), "Upper": [pct(min(x * 1.2, 0.40)) if x > 0 else pct(0) for x in w]},
                   index=W.index)
rng = rng[w > 0]
rng.loc["Total"] = ["", pct(w.sum(), 0), "", ""]
rng.index.name = "ETF"
r.table(rng, caption="Table 1. Strategic allocation and permitted ranges (±20% of each target, capped at the 40% "
        "single-ETF limit). ETFs with a 0% target are not held.")
r.p(f"<b>Expected characteristics</b> (J.P. Morgan 2026 assumptions): arithmetic return {pct(s['Expected return (arith.)'])}, "
    f"compound return of about {pct(s['Expected return (compound, approx.)'])}, volatility {pct(s['Volatility'])}; equities "
    f"{pct(s['Equities'],0)}, Treasuries {pct(s['Treasuries + TIPS'],0)}, credit {pct(s['Credit (LQD, HYG)'],0)}, gold "
    f"{pct(s['Gold + commodities'],0)}. The expected compound return exceeds the {pct(m['objective'])} hurdle, but only by "
    f"about {(s['Expected return (compound, approx.)'] - m['objective']) * 1e4:.0f} basis points.")
r.p("<b>Concentration warning.</b> The optimizer allocates 0% to US large caps and the maximum 40% to US REITs, because "
    "the assumptions give REITs the highest expected return of the 11 asset classes (8.8% compound vs. 6.7% for US "
    "large caps). The allocation also sits exactly on three limits (VNQ 40%, Treasuries 15%, gold 10%). Mean-variance "
    f"optimization concentrates in whichever assets have the highest estimated return. Lowering the REIT assumption by "
    f"2 percentage points, all else equal, cuts the REIT weight of the 12%-volatility portfolio from "
    f"{pct(SENS.loc['VNQ','VNQ -0%'],0)} to {pct(SENS.loc['VNQ','VNQ -2%'],0)} (Table A3). The Committee should adopt this allocation knowing that it is a "
    "large active bet on REITs and emerging markets relative to a market-cap-weighted portfolio.")

r.h1("6. Policy benchmark")
r.p(f"The policy benchmark is the strategic allocation in Table 1, invested in the same ETFs at their target weights "
    f"and rebalanced monthly: {', '.join(f'{pct(v,0)} {t}' for t, v in w[w > 0].items())}. Because the benchmark uses "
    f"the same vehicles, the difference between the Endowment's return and the benchmark measures implementation "
    f"(drift within ranges, trading costs and timing), not asset allocation. The Committee also monitors two "
    f"reference measures: the return objective (inflation + 4.9%) to judge whether the policy is meeting its goal, "
    f"and a 60% MSCI ACWI / 40% Bloomberg US Aggregate portfolio to judge the policy against a simple alternative.")

r.h1("7. Rebalancing")
r.bullets([
    "Staff check the weights at every month-end.",
    "If any holding is outside its range in Table 1 (±20% of its target, relative), staff rebalance the whole "
    "portfolio back to target weights at the next month-end close.",
    "Cash flows (spending, gifts) are used first to move weights towards targets, reducing trading.",
    "The asset-class limits in Section 4 govern the target allocation. They are not separate triggers for drifted "
    "weights, with one exception: no ETF may exceed 40% for more than one month-end.",
])
r.p(f"<b>Why the limits are not separate triggers.</b> Three targets sit exactly on a limit, so any drift would breach "
    f"one. On actual ETF returns from May 2007 to September 2026 ({m['n_months']} month-ends), the ±20% bands alone would "
    f"have triggered {m['band_events']} rebalances. Treating every limit as a trigger would have triggered "
    f"{m['band_hard_events']}, which means rebalancing almost every month, and allowing a 1-point tolerance would still "
    f"have triggered {m['band_hard_tol_events']}. Frequent rebalancing adds cost without improving risk control.")

r.h1("8. Monitoring and reporting")
r.bullets([
    "<b>Monthly (staff):</b> market value, weights vs. ranges, returns vs. the policy benchmark, any breaches.",
    "<b>Quarterly (Committee):</b> performance vs. benchmark and objective over 1, 3, 5 and 10 years; risk report "
    "(volatility, Value-at-Risk, Expected Shortfall, stress tests); spending calculation; rebalancing log.",
    "<b>Annually (Board):</b> a summary of results against the objective, risk limit, costs and this IPS.",
    "<b>Breaches:</b> any breach of this IPS is reported to the Committee chair within two business days with a "
    "plan to correct it.",
])

r.h1("9. Annual review")
r.p("The Committee reviews this IPS every year, after the consultant publishes updated capital market assumptions, "
    "and whenever the University's circumstances change materially (spending needs, a large gift, a change in the "
    "spending rule). The review re-runs the frontier and Monte Carlo analysis with the new assumptions, checks the "
    "allocation against the risk limit, reviews costs, and confirms or amends the allocation. The allocation is not "
    "changed because of recent performance alone. Any change is recorded with its reasons.")

r.pagebreak()
r.h1("Appendix A. Supporting analysis")
r.h2("A1. Capital market assumptions")
etf = A[A["ETF"].notna()]
cma = pd.DataFrame({"ETF": etf["ETF"].values, "Compound": etf["Compound 2026"].map(pct).values,
                    "Arithmetic": etf["Arithmetic 2026"].map(pct).values, "Volatility": etf["Volatility"].map(pct).values,
                    "Hist. arith. 2007–26": H["Hist. ann. return (arith.)"].map(pct).values,
                    "Hist. vol. 2007–26": H["Hist. volatility"].map(pct).values}, index=etf.index)
cma.index.name = "J.P. Morgan asset class"
r.table(cma, caption="Table A1. J.P. Morgan Asset Management 2026 Long-Term Capital Market Assumptions (U.S. dollar, "
        "10–15 year horizon, as of 30 September 2025), mapped to the closest ETF, with historical ETF figures for "
        f"comparison. Inflation assumption: {pct(m['inflation'])}. Cash: {pct(A.loc['U.S. Cash','Compound 2026'])}.", font=7.5)
r.image(F / "fig_frontier.png", 14, "Figure A1. Constrained efficient frontier and the three candidates.")
r.h2("A2. Candidates and Monte Carlo results")
cand = pd.DataFrame({k: {**{t: pct(W.loc[t, k], 0) for t in W.index},
                         "Expected return (arith.)": pct(ST.loc[k, 'Expected return (arith.)']),
                         "Volatility": pct(ST.loc[k, 'Volatility']),
                         "P(real value preserved, 20y)": pct(ST.loc[k, 'P(real value preserved, 20y)']),
                         "Median real value after 20y": f"${ST.loc[k, 'Median real value after 20y ($bn)']:.2f}bn",
                         "P(drawdown worse than −30%)": pct(ST.loc[k, 'P(drawdown worse than -30%)']),
                         "P(1-year loss worse than −20%)": pct(ST.loc[k, 'P(1-year loss worse than -20%)'], 2),
                         "Median real spending, year 1": f"${ST.loc[k, 'Median real spending yr 1 ($m)']:.1f}m",
                         "Median real spending, year 20": f"${ST.loc[k, 'Median real spending yr 20 ($m)']:.1f}m"}
                     for k in W.columns})
cand.index.name = ""
r.table(cand, caption="Table A2. Candidate weights and 10,000-path, 20-year Monte Carlo results. Spending in today's dollars.",
        font=7.5)
r.p("<b>Method.</b> Quarterly simulation over 20 years. Asset returns and inflation are drawn jointly from a "
    "multivariate lognormal distribution matching the J.P. Morgan arithmetic returns, volatilities and correlations "
    "(including inflation). Each quarter the portfolio is rebalanced to target, costs of 0.10% are deducted and "
    "spending of 1.125% of the trailing 12-quarter average value is paid. 'Real value preserved' means the market "
    "value after 20 years, deflated by simulated inflation, is at least $2.0bn. Drawdowns are measured on quarter-end "
    "nominal values after spending. The one-year loss probability uses calendar-year returns after costs and before "
    "spending, across all simulated years.")
r.image(F / "fig_real_spending.png", 14, "Figure A2. Median annual real spending for each candidate, with the 10th–90th "
        f"percentile band for {C}.")
sn = SENS.loc[(SENS > 0.001).any(axis=1)].map(lambda x: pct(x, 0))
sn.columns = ["Base case", "REIT return −1 pt", "REIT return −2 pts"]
sn.index.name = "ETF"
r.table(sn, caption="Table A3. Sensitivity of the 12%-volatility frontier portfolio to the REIT expected-return assumption.")
r.h2("A3. Historical cross-check")
hc = m["hist_chosen"]
r.p(f"Applied to actual ETF returns from May 2007 to September 2026 with the band rebalancing policy, the {C} "
    f"allocation returned {pct(hc['Ann. return'])} a year with {pct(hc['Volatility'])} volatility, a worst 12-month return of "
    f"{pct(hc['Worst 12-month return'])} (12 months to {pd.Timestamp(hc['Worst 12-month return ends']):%B %Y}) and a maximum "
    f"drawdown of {pct(hc['Max drawdown'])} (trough {pd.Timestamp(hc['Max drawdown trough']):%B %Y}). It also lost "
    f"{pct(-hc['Worst 12-month return 2022-23'])} over 12 months in 2022, when stocks and bonds fell together. Realised volatility was higher than the {pct(s['Volatility'])} assumed, and a −20% one-year loss, "
    f"which the model treats as a {pct(s['P(1-year loss worse than -20%)'],1)} event, happened twice in this sample. Normal and "
    f"lognormal models understate the probability of crises; the Committee should treat the risk limit as a floor "
    f"on caution, read the risk report's stress tests alongside it, and expect a drawdown of 40% or more in a severe crisis.")
r.image(F / "fig_ltcma_vs_history.png", 14, "Figure A3. Expected arithmetic returns: J.P. Morgan assumptions vs. 2007–2026 history.")
n = r.build()
print("pages:", n)
