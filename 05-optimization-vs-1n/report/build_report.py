"""Builds report/report.pdf from the CSV results written by notebooks/backtest.ipynb."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import pandas as pd

from common.report import Report

D, F = ROOT / "data", ROOT / "report" / "figures"
base = pd.read_csv(D / "results_base.csv", index_col=0)
boot = pd.read_csv(D / "bootstrap_vs_1n.csv", index_col=0)
w36 = pd.read_csv(D / "results_window36.csv", index_col=0)
c25 = pd.read_csv(D / "results_cost25.csv", index_col=0)
sub = pd.read_csv(D / "subperiods.csv", index_col=0)
meta = json.load(open(D / "meta.json"))
R = pd.read_csv(D / "etf_monthly_returns.csv", index_col=0, parse_dates=True)
W = {k: pd.read_csv(D / f"weights_{k}.csv", index_col=0)
     for k in ["max_sharpe", "risk_parity", "black-litterman", "min_variance"]}

pct = lambda x, d=1: f"{x * 100:.{d}f}%"
f2 = lambda x: f"{x:.2f}"
S = base["Sharpe"]
best = S.drop("1/N").idxmax()
ms_gap = S["Max Sharpe"] - S["1/N"]
oos = R.loc[meta["oos_start"]:meta["oos_end"]]
cagr_etf = ((1 + oos).prod() ** (12 / len(oos)) - 1).sort_values()
worst4 = list(cagr_etf.index[:4])

r = Report(ROOT / "report" / "report.pdf",
           "Does Optimization Beat 1/N? Evidence from an 11-ETF Multi-Asset Universe, 2012–2026",
           "Investment Research Portfolio · Project 6 · Data to 30 September 2026")

r.h1("Abstract")
r.abstract(
    f"DeMiguel, Garlappi and Uppal (2009) find that none of 14 optimizing models reliably beats "
    f"an equally weighted (1/N) portfolio out of sample. I re-run their question on 11 liquid US-listed "
    f"multi-asset ETFs with monthly rebalancing, a rolling 60-month estimation window, a 40% position "
    f"cap and 10 basis points of one-way trading costs, over {meta['n_months']} out-of-sample months "
    f"(May 2012 to September 2026). The classic 60/40 benchmark has the highest net Sharpe ratio "
    f"({f2(S['60/40'])} vs. {f2(S['1/N'])} for 1/N; stationary-bootstrap p = {boot.loc['60/40','p_value']:.3f}). "
    f"Contrary to the usual finding, the naive sample-moment maximum-Sharpe portfolio also beats 1/N "
    f"after costs (Sharpe {f2(S['Max Sharpe'])}, difference {ms_gap:+.2f}, p = {boot.loc['Max Sharpe','p_value']:.3f}), "
    f"but the result is fragile: it is insignificant with a 36-month window (p = {meta['p_window36']['Max Sharpe']:.3f}), "
    f"at 25 bp costs (p = {meta['p_cost25']['Max Sharpe']:.3f}) and in each subperiod on its own. Minimum variance, "
    f"risk parity and Black-Litterman are statistically indistinguishable from 1/N. In this period 1/N was a weak "
    f"benchmark: it held only 9% in SPY, which returned {pct(cagr_etf['SPY'])} a year (no other ETF exceeded "
    f"{pct(cagr_etf.drop('SPY').max())}), and 36% in {', '.join(worst4)}, the four worst performers.")

r.h1("1. Introduction")
r.p("Mean-variance optimization (Markowitz, 1952) is optimal only if expected returns and covariances are "
    "known. In practice they are estimated, and estimation error in expected returns is large enough that "
    "optimized portfolios often do worse out of sample than naive rules. DeMiguel, Garlappi and Uppal (2009, "
    "<i>Review of Financial Studies</i> 22(5), 1915–1953) showed that with realistic estimation windows the "
    "1/N rule is hard to beat in Sharpe ratio, certainty-equivalent return or turnover. This study asks the "
    "same question for a practitioner's multi-asset universe: <b>does any of five standard construction methods "
    "beat a simple equal-weight portfolio after transaction costs?</b>")
r.p("The six strategies span the main families used by multi-asset teams: a fixed benchmark (60/40), a "
    "risk-only optimizer (minimum variance with Ledoit-Wolf shrinkage), a full mean-variance optimizer with "
    "naive inputs (maximum Sharpe), a risk-budgeting rule (equal risk contribution) and a Bayesian blend of "
    "an equilibrium prior with a systematic view (Black-Litterman with a momentum view).")

r.h1("2. Data")
r.p(f"The universe is 11 US-listed ETFs covering every major liquid asset class: SPY, EFA, EEM (equities), "
    f"IEF, TLT, TIP (Treasuries and TIPS), LQD, HYG (credit), VNQ (REITs), GLD and DBC (real assets). Daily "
    f"dividend- and split-adjusted closing prices come from Yahoo Finance via yfinance; I convert them to "
    f"month-end total returns. HYG launched in April 2007, so the common sample runs from May 2007 to "
    f"September 2026 ({len(R)} months). The risk-free rate is the 3-month Treasury bill (FRED series TB3MS), "
    f"converted to a monthly rate. All inputs are saved in <font face='Courier'>/data</font>.")
d = R.agg(["mean", "std"]).T
d["mean"] *= 12; d["std"] *= 12 ** 0.5
d = d.assign(Sharpe=(d["mean"] - 0) / d["std"])
tab = pd.DataFrame({"Ann. mean": d["mean"].map(pct), "Ann. vol": d["std"].map(pct),
                    "Worst month": R.min().map(pct), "Best month": R.max().map(pct)})
tab.index.name = "ETF"
r.table(tab, caption="Table 1. Monthly total returns of the 11 ETFs, May 2007 – September 2026 (arithmetic mean ×12, "
        "volatility ×√12).")

r.h1("3. Method")
r.h2("3.1 Backtest design")
r.bullets([
    "Rolling estimation window of 60 months; weights for month t use only returns through month t−1. "
    "The first out-of-sample month is May 2012 and the last is September 2026.",
    "Monthly rebalancing to target weights; long-only; maximum 40% in any ETF.",
    "Trading costs of 10 bp one-way on turnover, where turnover is the sum of absolute differences between the "
    "new target and the drifted weights of the previous month. The initial purchase is not charged.",
])
r.h2("3.2 The six strategies")
r.bullets([
    "<b>1/N:</b> 9.09% in each ETF, rebalanced monthly.",
    "<b>60/40:</b> 60% SPY, 40% IEF, rebalanced monthly.",
    "<b>Minimum variance:</b> minimizes portfolio variance using the Ledoit-Wolf (2004) shrunk covariance matrix "
    "(constant-variance target), solved with PyPortfolioOpt.",
    "<b>Maximum Sharpe:</b> tangency portfolio from sample means and the sample covariance matrix of the window, "
    "with the window's average T-bill rate as the risk-free rate. In every window at least one ETF had a mean "
    "return above cash, so the tangency portfolio was always defined.",
    "<b>Risk parity:</b> equal risk contribution weights from the sample covariance matrix, solved with the "
    "convex formulation of Spinu (2013). The 40% cap never bound.",
    "<b>Black-Litterman:</b> prior weights SPY 35%, EFA 15%, EEM 5%, IEF 15%, TLT 5%, TIP 5%, LQD 10%, HYG 5%, "
    "VNQ 2%, GLD 2%, DBC 1%; risk aversion δ = 2.5; τ = 0.05; implied excess returns π = δΣw. Each month one "
    "relative view: the three ETFs with the highest 12-1 month momentum (months t−12 to t−2) outperform the "
    "three lowest by 3% a year, with 50% confidence using Idzorek's (2005) method. Final weights maximize "
    "μ'w − (δ/2)w'Σw on the posterior moments subject to the same long-only, 40% constraints.",
])
r.h2("3.3 Performance measures and test")
r.p("I report the annualized geometric return, annualized volatility, Sharpe and Sortino ratios of monthly "
    "excess returns over TB3MS (annualized by √12), maximum drawdown, Calmar ratio (return ÷ |max drawdown|), "
    "average monthly turnover and the effective number of holdings, 1/Σw². To test whether a Sharpe ratio "
    "differs from that of 1/N, I resample the paired monthly excess returns with the stationary bootstrap of "
    "Politis and Romano (1994), 5,000 draws, mean block length chosen by the Politis-White (2004) rule. The "
    "two-sided p-value is the share of re-centred bootstrap differences at least as large in absolute value "
    "as the observed difference.")

r.h1("4. Results")
fmt = pd.DataFrame({
    "Ann. return": base["Ann. return"].map(pct), "Vol.": base["Volatility"].map(pct),
    "Sharpe": base["Sharpe"].map(f2), "Sortino": base["Sortino"].map(f2),
    "Max DD": base["Max drawdown"].map(pct), "Calmar": base["Calmar"].map(f2),
    "Turnover /mo": base["Avg monthly turnover"].map(pct), "Eff. N": base["Effective N"].map(lambda x: f"{x:.1f}"),
    "Δ Sharpe vs 1/N": ["–"] + [f"{boot.loc[k, 'diff']:+.2f}" for k in base.index[1:]],
    "p-value": ["–"] + [f"{boot.loc[k, 'p_value']:.3f}" for k in base.index[1:]],
})
fmt.index.name = "Strategy"
r.table(fmt, caption="Table 2. Out-of-sample performance net of 10 bp one-way costs, May 2012 – September 2026 "
        f"({meta['n_months']} months). p-values from a 5,000-draw stationary bootstrap of the Sharpe difference vs. 1/N.",
        font=7.5)
r.p(f"<b>60/40 wins.</b> The two-asset benchmark has the highest net Sharpe ratio ({f2(S['60/40'])}) and the "
    f"highest return ({pct(base.loc['60/40','Ann. return'])} a year). Its advantage over 1/N is the only one "
    f"that is significant at 5% and also survives every robustness check below. This is not an optimization result: "
    f"it reflects the exceptional run of US large caps after 2012.")
r.p(f"<b>Naive maximum Sharpe beats 1/N here, unlike in DeMiguel et al.</b> Its net Sharpe ratio is "
    f"{f2(S['Max Sharpe'])} against {f2(S['1/N'])} for 1/N (p = {boot.loc['Max Sharpe','p_value']:.3f}). "
    f"Two features of this experiment favour it. First, the 40% cap and long-only constraint act as strong "
    f"shrinkage (Jagannathan and Ma, 2003): the optimizer cannot take the extreme positions that ruin "
    f"unconstrained mean-variance portfolios. Second, momentum in asset-class returns was persistent: the "
    f"optimizer held SPY and Treasuries through the 2010s and moved into gold and commodities after 2022, "
    f"just before gold's rally (Figure 3). It pays for this with average monthly turnover of "
    f"{pct(base.loc['Max Sharpe','Avg monthly turnover'])}, about "
    f"{base.loc['Max Sharpe','Avg monthly turnover'] / base.loc['1/N','Avg monthly turnover']:.0f} times that of 1/N, "
    f"which costs it {base.loc['Max Sharpe','Sharpe (gross)'] - S['Max Sharpe']:.2f} of Sharpe ratio at 10 bp.")
r.p(f"<b>Risk-based methods do not beat 1/N.</b> Minimum variance halves volatility "
    f"({pct(base.loc['Min variance','Volatility'])}) and has the smallest drawdown, but its bond-heavy portfolio "
    f"(on average {pct(W['min_variance'][['IEF','TIP']].mean().sum(),0)} in IEF and TIP) earned little and was hit "
    f"by 2022. Its Sharpe ratio ({f2(S['Min variance'])}) is the lowest of the six. Risk parity is close to 1/N in "
    f"Sharpe ({f2(S['Risk parity'])}, p = {boot.loc['Risk parity','p_value']:.2f}) with lower volatility.")
r.p(f"<b>Black-Litterman</b> earns a Sharpe ratio of {f2(S['Black-Litterman'])} with the second-smallest drawdown of the six "
    f"({pct(base.loc['Black-Litterman','Max drawdown'])}, after minimum variance), but the monthly momentum "
    f"view flips often and turnover is {pct(base.loc['Black-Litterman','Avg monthly turnover'])} a month, the "
    f"highest of all. Its advantage over 1/N is not significant (p = {boot.loc['Black-Litterman','p_value']:.2f}).")
r.image(F / "fig1_cumulative.png", 15.5, "Figure 1. Growth of $1 invested in May 2012, net of 10 bp one-way costs.")
r.image(F / "fig2_rolling_sharpe.png", 15.5, "Figure 2. Rolling 36-month Sharpe ratio of net excess returns. "
        "Rankings are unstable: every strategy except 60/40 spends long stretches below 1/N.")
r.image(F / "fig3_weights.png", 16.5, "Figure 3. Monthly target weights of the maximum Sharpe and risk parity "
        "portfolios. Maximum Sharpe concentrates in 3–4 ETFs and hits the 40% cap most months; risk parity "
        "keeps every ETF and changes slowly.")
r.image(F / "fig4_sharpe_costs.png", 15, "Figure 4. Sharpe ratio before and after 10 bp one-way costs. Costs matter "
        "most for the two strategies with high turnover, maximum Sharpe and Black-Litterman.")

r.h1("5. Robustness")
rob = pd.DataFrame({
    "Sharpe 60m, 10bp": base["Sharpe"].map(f2),
    "p vs 1/N": ["–"] + [f"{boot.loc[k,'p_value']:.3f}" for k in base.index[1:]],
    "Sharpe 36m, 10bp": w36["Sharpe"].map(f2),
    "p vs 1/N ": ["–"] + [f"{meta['p_window36'][k]:.3f}" for k in base.index[1:]],
    "Turnover 36m": w36["Avg monthly turnover"].map(pct),
    "Sharpe 60m, 25bp": c25["Sharpe"].map(f2),
    "p vs 1/N  ": ["–"] + [f"{meta['p_cost25'][k]:.3f}" for k in base.index[1:]],
})
rob.index.name = "Strategy"
r.table(rob, caption="Table 3. Robustness. The 36-month window is evaluated over the same May 2012 – September 2026 "
        "months as the base case, so only the estimation window changes.", font=7.5)
r.p(f"With a 36-month window, estimation error rises and turnover of the maximum Sharpe portfolio increases "
    f"from {pct(base.loc['Max Sharpe','Avg monthly turnover'])} to {pct(w36.loc['Max Sharpe','Avg monthly turnover'])} "
    f"a month; its Sharpe ratio falls to {f2(w36.loc['Max Sharpe','Sharpe'])} and the difference from 1/N is no longer "
    f"significant (p = {meta['p_window36']['Max Sharpe']:.3f}). At 25 bp costs it falls to {f2(c25.loc['Max Sharpe','Sharpe'])} "
    f"(p = {meta['p_cost25']['Max Sharpe']:.3f}) and Black-Litterman falls to {f2(c25.loc['Black-Litterman','Sharpe'])}. "
    f"The 60/40 result is unchanged in both cases.")
sb = pd.DataFrame({c: sub[c].map(lambda x: "–" if pd.isna(x) else f"{x:.2f}" if "Sharpe" in c else f"{x:.3f}")
                   for c in sub.columns})
sb.index.name = "Strategy"
r.table(sb, caption="Table 4. Subperiods. Sharpe ratios and bootstrap p-values vs. 1/N, before and after 2024.",
        font=7.5)
r.p(f"Splitting the sample shows how fragile the optimizer's win is. Before 2024, maximum Sharpe's lead over "
    f"1/N is not significant (p = {sub.loc['Max Sharpe','May 2012 - Dec 2023 p vs 1/N']:.2f}). Its full-sample "
    f"significance comes from combining a modest, noisy lead in 2012–2023 with a very strong 2024–2026 "
    f"(Sharpe {sub.loc['Max Sharpe','Jan 2024 - Sep 2026 Sharpe']:.2f}), when it held up to 40% gold. Only 60/40's "
    f"lead is significant in the long first subperiod.")

r.h1("6. Conclusion")
r.p(f"In this 11-ETF universe over 2012–2026, the answer to DeMiguel, Garlappi and Uppal's question is mixed. "
    f"None of the risk-based optimizers beats 1/N. The naive maximum-Sharpe optimizer does beat 1/N after "
    f"10 bp costs, by {ms_gap:.2f} of Sharpe ratio, but the result is not robust to a shorter estimation window, "
    f"higher costs or splitting the sample, so I would not rely on it. The strongest result is that a plain "
    f"60/40 portfolio beat everything, which says more about the period (US large caps returned {pct(cagr_etf['SPY'])} a year while "
    f"Treasuries, TIPS and commodities returned {pct(cagr_etf[worst4].min())} to {pct(cagr_etf[worst4].max())}) "
    f"than about portfolio construction. For an allocator the practical "
    f"lessons are: constraints are a form of shrinkage and make optimizers far less fragile; turnover costs "
    f"must be in the backtest; and an equal-weight benchmark is only meaningful if the universe itself is "
    f"chosen sensibly.")
r.h1("Limitations")
r.bullets([
    "One 14-year out-of-sample path; the 2012–2026 period favoured US large caps, which flatters 60/40.",
    "The ETF universe was chosen in 2026 with hindsight; all 11 funds survived.",
    "Costs are a flat 10 bp one-way; there are no taxes, bid-ask spreads beyond that, or market impact.",
    "Yahoo Finance adjusted prices assume dividends are reinvested at the close on the ex-date.",
])
r.h1("Appendix")
cy = pd.read_csv(D / "net_returns_base.csv", index_col=0, parse_dates=True)
cal = ((1 + cy).groupby(cy.index.year).prod() - 1)
cal.index = [f"{y}" + (" (May–Dec)" if y == 2012 else " (Jan–Sep)" if y == 2026 else "") for y in cal.index]
cal.index.name = "Year"
r.table(cal.map(pct), caption="Table A1. Calendar-year net returns by strategy.", font=7.5)
avgw = pd.DataFrame({"Min variance": W["min_variance"].mean(), "Max Sharpe": W["max_sharpe"].mean(),
                     "Risk parity": W["risk_parity"].mean(), "Black-Litterman": W["black-litterman"].mean(),
                     "BL prior": pd.Series({"SPY": .35, "EFA": .15, "EEM": .05, "IEF": .15, "TLT": .05,
                                            "TIP": .05, "LQD": .10, "HYG": .05, "VNQ": .02, "GLD": .02, "DBC": .01})})
avgw.loc["Months at 40% cap (any ETF)"] = [
    int((W[k].max(axis=1) > 0.3999).sum()) for k in ["min_variance", "max_sharpe", "risk_parity", "black-litterman"]] + [0]
fa = avgw.copy().astype(object)
fa.iloc[:-1] = avgw.iloc[:-1].map(pct)
fa.iloc[-1] = avgw.iloc[-1].astype(int).astype(str)
fa.index.name = "ETF"
r.table(fa, caption="Table A2. Average target weights over the out-of-sample period, and the number of months "
        f"(out of {meta['n_months']}) in which at least one ETF was at the 40% cap.", font=7.5)
etf_t = pd.DataFrame({"Ann. return 2012–26": cagr_etf.map(pct)}).T
r.table(etf_t, caption="Table A3. Annualized total return of each ETF over the out-of-sample period.", font=7.5,
        index=False)
r.h1("References")
r.bullets([
    "DeMiguel, V., Garlappi, L. and Uppal, R. (2009). Optimal Versus Naive Diversification: How Inefficient Is "
    "the 1/N Portfolio Strategy? <i>Review of Financial Studies</i>, 22(5), 1915–1953.",
    "Idzorek, T. (2005). A Step-by-Step Guide to the Black-Litterman Model. Working paper.",
    "Jagannathan, R. and Ma, T. (2003). Risk Reduction in Large Portfolios: Why Imposing the Wrong Constraints "
    "Helps. <i>Journal of Finance</i>, 58(4), 1651–1683.",
    "Ledoit, O. and Wolf, M. (2004). Honey, I Shrunk the Sample Covariance Matrix. <i>Journal of Portfolio "
    "Management</i>, 30(4), 110–119.",
    "Politis, D. and Romano, J. (1994). The Stationary Bootstrap. <i>JASA</i>, 89(428), 1303–1313.",
    "Politis, D. and White, H. (2004). Automatic Block-Length Selection for the Dependent Bootstrap. "
    "<i>Econometric Reviews</i>, 23(1), 53–70.",
    "Spinu, F. (2013). An Algorithm for Computing Risk Parity Weights. SSRN 2297383.",
])
print("pages:", r.build())
