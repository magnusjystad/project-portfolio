"""Builds the 10-slide board presentation (report/board_presentation.pdf)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import pandas as pd

from common.slides import Deck

D, F = ROOT / "data", ROOT / "report" / "figures"
W = pd.read_csv(D / "candidate_weights.csv", index_col=0)
ST = pd.read_csv(D / "candidate_stats.csv", index_col=0)
A = pd.read_csv(D / "ltcma2026_usd_assumptions.csv", index_col=0)
POL = pd.read_csv(D / "final_policy_weights.csv", index_col=0)["weight"]
PS = pd.read_csv(D / "final_policy_stats.csv", index_col=0).iloc[:, 0]
m = json.load(open(D / "meta.json"))
SENS = pd.read_csv(D / "sensitivity_reit_assumption.csv", index_col=0)
hc = m["hist_chosen"]
pct = lambda x, d=1: f"{x * 100:.{d}f}%"
C = m["chosen"]

d = Deck(ROOT / "report" / "board_presentation.pdf",
         "Northbridge University Endowment · Strategic asset allocation review · Fictional client · "
         "Assumptions: J.P. Morgan 2026 LTCMA (USD), as of 30 Sep 2025")

d.title("Strategic Asset Allocation", "Northbridge University Endowment · Recommendation to the Investment Committee",
        [f"Recommendation: adopt the {C} allocation ({pct(PS['Volatility'])} expected volatility)",
         f"Expected return {pct(PS['Expected return (compound, approx.)'])} compound vs. {pct(m['objective'])} required",
         f"{pct(PS['P(real value preserved, 20y)'],0)} probability of preserving real value over 20 years",
         "Decisions requested: allocation, ranges, benchmark, rebalancing policy"])

d.bullets("The Endowment's mandate", [
    "$2.0bn, perpetual horizon, liquid ETFs only (11-fund universe)",
    "Spending: 4.5% a year of the trailing 12-quarter average market value",
    f"Costs: 0.40% a year → return objective inflation + 4.9% = {pct(m['objective'])} nominal (compound)",
    "Risk limit: expected volatility ≤ 12% and ≤ 5% probability of a one-year loss worse than −20%",
    "Constraints: max 40% per ETF; equities 40–70%; Treasuries + TIPS ≥ 15%; gold + commodities ≤ 10%",
    "Goal: intergenerational equity — future students receive the same real support as today's",
], subtitle="Fixed client profile")

cma = A[A["ETF"].notna()][["ETF", "Compound 2026", "Volatility"]].copy()
cma["Compound 2026"] = cma["Compound 2026"].map(pct)
cma["Volatility"] = cma["Volatility"].map(pct)
cma.columns = ["ETF", "Expected return (compound)", "Volatility"]
d.table("Capital market assumptions", cma, subtitle="J.P. Morgan Asset Management 2026 LTCMA, U.S. dollar, 10–15 years",
        note=f"Inflation {pct(m['inflation'])} · Cash {pct(A.loc['U.S. Cash','Compound 2026'])} · REITs and emerging "
             f"markets have the highest expected returns", font=11.5, col_width=[0.12, 0.25, 0.15])

d.image("The efficient frontier under the IPS constraints", F / "fig_frontier.png",
        subtitle="Three candidates at 8%, 10% and 12% expected volatility",
        note=f"Only Growth clears the {pct(m['objective'])} compound hurdle (compound: Balanced {pct(ST.loc['Balanced','Expected return (compound, approx.)'])}, Growth {pct(ST.loc['Growth','Expected return (compound, approx.)'])})")

d.image("Three candidate allocations", F / "fig_candidates.png", subtitle="Weights from the constrained optimizer",
        note="All three hold 0% US large caps and 29–40% REITs: the optimizer follows the highest assumed returns",
        box=(0.06, 0.13, 0.88, 0.68))

mc = pd.DataFrame({k: {"Expected return (arith.)": pct(ST.loc[k, "Expected return (arith.)"]),
                       "Expected volatility": pct(ST.loc[k, "Volatility"]),
                       "P(real value preserved, 20y)": pct(ST.loc[k, "P(real value preserved, 20y)"]),
                       "Median real value after 20y": f"${ST.loc[k, 'Median real value after 20y ($bn)']:.2f}bn",
                       "P(drawdown worse than −30%)": pct(ST.loc[k, "P(drawdown worse than -30%)"]),
                       "P(1-year loss < −20%)": pct(ST.loc[k, "P(1-year loss worse than -20%)"], 2),
                       "Median real spending, year 20": f"${ST.loc[k, 'Median real spending yr 20 ($m)']:.0f}m"}
                   for k in W.columns})
d.table("Monte Carlo: 10,000 paths × 20 years", mc, subtitle="Spending rule, costs and J.P. Morgan inflation applied quarterly",
        note=f"{C} has the highest chance of preserving real value and meets the risk limit → selected by the rule",
        font=12, col_width=[0.2, 0.2, 0.2])

d.image("What the recommended allocation means for spending", F / "fig_real_value_fan.png",
        subtitle=f"{C}: real market value after spending and costs, percentiles of 10,000 paths",
        note=f"Median real value after 20 years ${ST.loc[C, 'Median real value after 20y ($bn)']:.2f}bn · "
             f"{pct(ST.loc[C, 'P(drawdown worse than -30%)'],0)} chance of a drawdown worse than −30% along the way")

pol = pd.DataFrame({"Target": POL[POL > 0].map(lambda x: pct(x, 0)),
                    "Range": [f"{pct(x*0.8)} – {pct(min(x*1.2, 0.4))}" for x in POL[POL > 0]]})
d.table(f"Recommendation: the {C} allocation", pol, subtitle="Rounded to whole percentages within every limit; ±20% relative ranges",
        note=f"Expected return {pct(PS['Expected return (arith.)'])} arithmetic, {pct(PS['Expected return (compound, approx.)'])} compound · "
             f"volatility {pct(PS['Volatility'])} · P(real value preserved) {pct(PS['P(real value preserved, 20y)'])}",
        font=13, col_width=[0.2, 0.3], box=(0.2, 0.2, 0.6, 0.6))

d.bullets("Risks the Committee should accept knowingly", [
    "Concentration: 40% REITs and 0% US large caps — a large bet against the market-cap-weighted world portfolio",
    f"  It rests on one assumption (REITs 8.8% vs US large caps 6.7%): with REITs 2 points lower, the REIT weight falls "
    f"from {pct(SENS.loc['VNQ','VNQ -0%'],0)} to {pct(SENS.loc['VNQ','VNQ -2%'],0)}",
    f"History is harsher than the model: on 2007–2026 ETF returns this allocation had {pct(hc['Volatility'])} volatility",
    f"  Worst 12 months {pct(hc['Worst 12-month return'])} (to Feb 2009); {pct(hc['Worst 12-month return 2022-23'])} in 2022 — "
    f"the model calls a −20% year a {pct(PS['P(1-year loss worse than -20%)'],1)} event",
    f"Thin margin: expected compound return beats the {pct(m['objective'])} hurdle by about "
    f"{(PS['Expected return (compound, approx.)'] - m['objective']) * 1e4:.0f} bp; {pct(1 - PS['P(real value preserved, 20y)'],0)} "
    "chance real value is not preserved",
    "Mitigants: liquid ETFs, smoothed spending rule, quarterly risk report with stress tests",
], subtitle="Model limitations and what history shows")

d.bullets("Implementation and decisions requested", [
    "Policy benchmark: the target allocation in the same ETFs, rebalanced monthly",
    f"Rebalancing: month-end check; full rebalance when a holding leaves its ±20% range "
    f"({m['band_events']} times in 2007–2026)",
    f"  The IPS limits apply to targets, not drifted weights — otherwise {m['band_hard_events']} rebalances in {m['n_months']} months",
    "Reporting: monthly to staff, quarterly risk and performance to the Committee, annual to the Board",
    "Annual review after new capital market assumptions; no changes on recent performance alone",
    "Decisions: (1) adopt the allocation and ranges, (2) adopt the benchmark, (3) adopt the rebalancing policy",
], subtitle="For approval")
n = d.close()
print("slides:", n)
