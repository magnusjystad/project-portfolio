"""Builds report/report.pdf from the results written by notebooks/factors.ipynb."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import pandas as pd

from common.report import Report

D, FG = ROOT / "data", ROOT / "report" / "figures"
rd = lambda n: pd.read_csv(D / f"{n}.csv", index_col=0)
A1, A2, Cf, C10 = rd("A1_factor_summary"), rd("A2_decades"), rd("A3_corr_full"), rd("A3_corr_since2010")
A4r, A4i, A6 = rd("A4_recession"), rd("A4_inflation"), rd("A6_blend")
B2, B3, ES = rd("B2_regressions"), rd("B3_target_check"), rd("B_etf_stats")
roll = pd.read_csv(D / "rolling_target_loadings.csv", index_col=0, parse_dates=True)
m = json.load(open(D / "meta.json"))
a5 = m["A5"]
pct = lambda x, d=1: f"{x * 100:.{d}f}%"
f2 = lambda x: f"{x:.2f}"
FAC = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]
TGT = {"MTUM": "Mom", "VLUE": "HML", "QUAL": "RMW", "SIZE": "SMB", "USMV": "Mkt-RF"}
fs, fe = pd.Timestamp(m["factor_start"]), pd.Timestamp(m["factor_end"])
rs, re_ = pd.Timestamp(m["reg_start"]), pd.Timestamp(m["reg_end"])

r = Report(ROOT / "report" / "report.pdf",
           f"Factor Premia since 1963, and Do Factor ETFs Deliver Them?",
           f"Investment Research Portfolio · Project 7 · Factor data {fs:%B %Y} – {fe:%B %Y}")

best_single = A6.drop("Blend")["Sharpe"].max()
r.h1("Summary")
r.abstract(
    f"Over {m['n_factor']} months from {fs:%B %Y} to {fe:%B %Y}, the US market and momentum premia were the largest "
    f"({pct(A1.loc['Mkt-RF','Premium (ann.)'])} and {pct(A1.loc['Mom','Premium (ann.)'])} a year, t = "
    f"{A1.loc['Mkt-RF','t-stat']:.1f} and {A1.loc['Mom','t-stat']:.1f}). Value, profitability and investment earned "
    f"about 3% a year each and are significant over the full sample, while size ({pct(A1.loc['SMB','Premium (ann.)'])}, "
    f"t = {A1.loc['SMB','t-stat']:.1f}) is not. Every factor had long losing stretches: value lost "
    f"{pct(-a5['HML cum. return Jan 2007 - Dec 2020'],0)} from January 2007 to December 2020 and has since recovered "
    f"{pct(a5['Share of 2007-2020 loss recovered'],0)} of that loss. An equal-weight blend of value, profitability, "
    f"investment and momentum had a Sharpe ratio of {f2(A6.loc['Blend','Sharpe'])}, against {f2(best_single)} for the best "
    f"single factor. In Part B, all five iShares factor ETFs load significantly on their target factor, but "
    f"the size of the exposure differs widely: MTUM carries {f2(B2.loc['MTUM','Mom'])} units of the momentum factor and "
    f"VLUE {f2(B2.loc['VLUE','HML'])} units of value, while QUAL ({f2(B2.loc['QUAL','RMW'])} on profitability) and SIZE "
    f"({f2(B2.loc['SIZE','SMB'])} on size) are close to the market portfolio with a small tilt. No ETF has a significant alpha.")

r.h1("1. Data")
r.bullets([
    f"<b>Factors:</b> Fama/French 5 Factors (2x3) and the Momentum Factor, monthly, from the Kenneth French Data "
    f"Library, {fs:%B %Y} to {fe:%B %Y} ({m['n_factor']} months; {fe:%B %Y} is the latest month published at the time of "
    f"writing). Mkt-RF is the value-weighted US market minus the one-month T-bill; SMB (small minus big), HML (high "
    f"minus low book-to-market), RMW (robust minus weak profitability), CMA (conservative minus aggressive "
    f"investment) and Mom (winners minus losers over months t−12 to t−2) are long-short portfolios.",
    "<b>Macro:</b> NBER recession indicator (FRED USREC) and CPI for all urban consumers (FRED CPIAUCSL). FRED has no "
    "CPI value for October 2025 because the Bureau of Labor Statistics did not publish one during the government "
    "shutdown, so that month is excluded from the inflation split only.",
    f"<b>ETFs:</b> iShares MSCI USA Momentum Factor (MTUM), Quality Factor (QUAL), Value Factor (VLUE), Min Vol Factor "
    f"(USMV) and Size Factor (SIZE). Daily adjusted closes from yfinance converted to monthly total returns. "
    f"Regressions run from {rs:%B %Y} to {re_:%B %Y} ({m['n_reg']} months), ending with the factor data.",
])

r.h1("Part A. Sixty-three years of factor returns")
r.h2("A1. Premium, risk and significance")
t1 = pd.DataFrame({"Premium /yr": A1["Premium (ann.)"].map(pct), "Volatility": A1["Volatility"].map(pct),
                   "Sharpe": A1["Sharpe"].map(f2), "t-stat": A1["t-stat"].map(f2),
                   "Max drawdown": A1["Max drawdown"].map(pct), "Worst 5y /yr": A1["Worst 5y (ann.)"].map(pct)})
t1.index.name = "Factor"
r.table(t1, caption=f"Table 1. Factor statistics, {fs:%b %Y} – {fe:%b %Y}. Premium = mean monthly return × 12; volatility × √12; "
        "t-stat = mean ÷ (standard deviation ÷ √T). Drawdowns and the worst rolling 5-year return use compounded returns.")
r.p(f"The market and momentum premia are the largest and most significant, at about 7% a year each. Momentum's "
    f"t-statistic of {A1.loc['Mom','t-stat']:.1f} is the highest of the six. Value, profitability and investment each earned around 3% a year with "
    f"t-statistics between 2.7 and 3.2. Size is the weakest: {pct(A1.loc['SMB','Premium (ann.)'])} a year with a "
    f"t-statistic of {A1.loc['SMB','t-stat']:.2f}, below the conventional 2.0 threshold, so over this sample it is not "
    f"distinguishable from zero. Factor investing is not a smooth ride: four of the six factors suffered drawdowns "
    f"above 55%, and all six had at least one five-year stretch with a negative compounded return.")
r.h2("A2. Decade by decade")
t2 = A2.map(pct); t2.index.name = "Decade"
r.table(t2, caption="Table 2. Annualized compounded return of each factor by decade.")
r.p("Premia come in long waves. Value earned 5–8% a year in the 1970s, 1980s and 2000s but lost money in the 1990s "
    "and 2010s. Momentum was strong in every decade until the 2000s, when the 2009 momentum crash pushed it negative. "
    "The 2010s and 2020s have been unusually poor for every long-short factor while the market itself earned over "
    "12% a year, which explains much of the frustration with factor products in that period.")
r.image(FG / "fig_cumulative_factors.png", 15.5, "Figure 1. Growth of $1 in each factor and in the equal-weight blend, "
        "log scale. Long-short factors are shown without the T-bill return.")
r.h2("A3. Correlations")
c = pd.concat([Cf.round(2).astype(str), C10.round(2).astype(str)], axis=1, keys=["Full", "Since 2010"])
c.columns = [f"{a[:4]} {b}" if a == "Full" else f"2010+ {b}" for a, b in c.columns]
c.index.name = "Factor"
r.table(c, caption=f"Table 3. Correlation matrix of monthly factor returns, full sample (left) and January 2010 – {fe:%B %Y} (right).",
        font=6.8)
r.p(f"HML and CMA are the most closely related pair ({Cf.loc['HML','CMA']:.2f} full sample, {C10.loc['HML','CMA']:.2f} since 2010): "
    f"value firms tend to be conservative investors, which is why Fama and French (2015) find HML largely redundant once "
    f"CMA and RMW are included. Momentum is negatively correlated with value ({Cf.loc['HML','Mom']:.2f}; {C10.loc['HML','Mom']:.2f} "
    f"since 2010), which is the basis of the classic value-momentum combination. Since 2010, SMB has become more "
    f"correlated with HML ({C10.loc['SMB','HML']:.2f} vs. {Cf.loc['SMB','HML']:.2f}) and the market.")
r.h2("A4. Regimes: recessions and high inflation")
t4 = pd.DataFrame({
    "Recession": A4r.iloc[:, 0].map(lambda x: pct(x, 2)), "Expansion": A4r.iloc[:, 1].map(lambda x: pct(x, 2)),
    "t (diff.)": A4r["Welch t"].map(f2),
    "CPI > 4%": A4i.iloc[:, 0].map(lambda x: pct(x, 2)), "CPI ≤ 4%": A4i.iloc[:, 1].map(lambda x: pct(x, 2)),
    "t (diff.) ": A4i["Welch t"].map(f2)})
t4.index.name = "Factor"
r.table(t4, caption=f"Table 4. Average monthly factor returns by regime. NBER recessions: {m['n_recession']} of {m['n_rec_sample']} months. "
        f"Year-on-year CPI inflation above 4%: {m['n_infl']} of {m['n_infl_sample']} months. t = Welch t-statistic for the difference.")
r.p(f"The market premium is much lower in recessions ({pct(A4r.loc['Mkt-RF'].iloc[0],2)} vs. "
    f"{pct(A4r.loc['Mkt-RF'].iloc[1],2)} a month) and when inflation is above 4% "
    f"({pct(A4i.loc['Mkt-RF'].iloc[0],2)} vs. {pct(A4i.loc['Mkt-RF'].iloc[1],2)}; t = {A4i.loc['Mkt-RF','Welch t']:.2f}). "
    f"None of the long-short factors has a premium that differs significantly between regimes: the largest effects are "
    f"CMA doing better in recessions (t = {A4r.loc['CMA','Welch t']:.2f}) and momentum doing worse "
    f"(t = {A4r.loc['Mom','Welch t']:.2f}). With only {m['n_recession']} recession months, these splits have little "
    f"statistical power, so the safest reading is that the style factors are not reliable recession hedges, but "
    f"they also did not lose money on average when the market did.")
r.h2("A5. Value's lost decade")
r.p(f"From January 2007 to December 2020, HML compounded at {pct(a5['HML ann. return Jan 2007 - Dec 2020'])} a year, "
    f"a cumulative loss of {pct(-a5['HML cum. return Jan 2007 - Dec 2020'])}, with the trough in "
    f"{pd.Timestamp(a5['Trough month']):%B %Y}. For comparison, HML earned {pct(a5['HML ann. return Jul 1963 - Dec 2006'])} a year "
    f"from July 1963 to December 2006. Explanations offered in the literature include the rising importance of intangible "
    f"assets that book value does not capture, falling interest rates that favoured long-duration growth stocks, and "
    f"crowding. From January 2021 to {fe:%B %Y}, HML returned {pct(a5[f'HML cum. return Jan 2021 - {fe:%b %Y}'])} cumulatively. "
    f"Because a {pct(-a5['HML cum. return Jan 2007 - Dec 2020'],0)} loss needs a "
    f"{pct(1/(1+a5['HML cum. return Jan 2007 - Dec 2020'])-1,0)} gain to recover, this has made back "
    f"{pct(a5['Share of 2007-2020 loss recovered'],0)} of the dollar loss: value has recovered strongly, but not fully.")
r.image(FG / "fig_value_lost_decade.png", 15, "Figure 2. Cumulative HML return since 2000, log scale; shaded: January 2007 – December 2020.")
r.h2("A6. A multi-factor blend")
t6 = pd.DataFrame({"Premium /yr": A6["Premium (ann.)"].map(pct), "Volatility": A6["Volatility"].map(pct),
                   "Sharpe": A6["Sharpe"].map(f2), "Max drawdown": A6["Max drawdown"].map(pct)})
t6.index.name = "Portfolio"
r.table(t6, caption="Table 5. Equal-weight blend of HML, RMW, CMA and Mom (rebalanced monthly) vs. each factor alone.")
r.p(f"Because the four factors are weakly or negatively correlated, combining them cuts volatility to "
    f"{pct(A6.loc['Blend','Volatility'])} while keeping a {pct(A6.loc['Blend','Premium (ann.)'])} premium. The Sharpe ratio rises "
    f"to {f2(A6.loc['Blend','Sharpe'])}, about {A6.loc['Blend','Sharpe']/best_single:.1f} times the best single factor, and the maximum "
    f"drawdown falls to {pct(A6.loc['Blend','Max drawdown'])}. Diversifying across factors is the most reliable way to "
    f"harvest them.")
r.image(FG / "fig_rolling_10y_premia.png", 15.5, "Figure 3. Rolling 10-year average premium of each factor. Every factor, "
        "including the market, has had decade-long windows with a negative average premium.")

r.h1("Part B. Do factor ETFs deliver their factor?")
r.p(f"For each ETF I regress the monthly return minus the one-month T-bill on the six factors, {rs:%B %Y} – {re_:%B %Y}: "
    "r − rf = α + β<sub>M</sub>(Mkt−RF) + s·SMB + h·HML + p·RMW + c·CMA + m·Mom + ε. Standard errors are Newey-West with "
    "three lags. A loading of 1 on a long-short factor would mean the ETF carries as much of that factor as the "
    "Fama-French research portfolio itself.")
t7 = pd.DataFrame({"Alpha /yr": B2["Alpha (ann.)"].map(pct), "t(α)": B2["t(alpha)"].map(f2)})
for f in FAC:
    t7[f] = [f"{b:.2f} ({t:.1f})" for b, t in zip(B2[f], B2[f"t({f})"])]
t7["R²"] = B2["R2"].map(f2)
t7.index.name = "ETF"
r.table(t7, caption="Table 6. Six-factor regressions; loadings with Newey-West t-statistics in brackets.", font=7.2)
r.image(FG / "fig_etf_loadings.png", 16, "Figure 4. Headline result: factor loadings of the five ETFs. The boxed cell is the "
        "factor each ETF is named after. For USMV the target is a market beta below 1 (t vs. 1 = "
        f"{B3.loc['USMV','t-stat']:.1f}).")
t8 = B3.copy()
t8["Target loading"] = t8["Target loading"].astype(float).map(f2)
t8["t-stat"] = t8["t-stat"].astype(float).map(f2)
t8.columns = ["Target", "Loading", "t-stat", "Largest style loading", "Delivers?"]
t8.index.name = "ETF"
r.table(t8, caption="Table 7. Is the target factor the ETF's largest exposure? For MTUM, VLUE, QUAL and SIZE the comparison is "
        "among the five style factors (every long-only equity fund has a market beta near 1). For USMV the t-stat tests β = 1.")
r.p(f"<b>All five ETFs deliver a statistically significant exposure to their target, and for MTUM, VLUE, QUAL and SIZE "
    f"it is their largest style exposure.</b> The magnitudes differ a lot. MTUM ({f2(B2.loc['MTUM','Mom'])}) and VLUE "
    f"({f2(B2.loc['VLUE','HML'])}) carry close to half of a pure long-short factor, which is a lot for a long-only "
    f"fund. QUAL ({f2(B2.loc['QUAL','RMW'])}) and SIZE ({f2(B2.loc['SIZE','SMB'])}) are mostly market exposure: their R² values "
    f"are {B2.loc['QUAL','R2']:.2f} and {B2.loc['SIZE','R2']:.2f} and market betas are near 1. USMV delivers what it promises, a "
    f"market beta of {f2(B2.loc['USMV','Mkt-RF'])}, and it also has a larger profitability loading "
    f"({f2(B2.loc['USMV','RMW'])}) than QUAL itself: low-volatility stocks tend to be profitable, conservative firms. "
    f"None of the five ETFs has an alpha significantly different from zero after accounting for these exposures.")
r.image(FG / "fig_rolling_target_loading.png", 15.5, "Figure 5. Rolling 36-month loading on each ETF's target factor.")
r.p(f"Exposures change over time. VLUE's value loading rose from about {roll['VLUE'].iloc[0]:.2f} in the first 36-month window "
    f"to {roll['VLUE'].iloc[-1]:.2f} in the latest. MTUM's momentum loading rose from about {roll['MTUM'].iloc[0]:.2f} to "
    f"{roll['MTUM'].iloc[-1]:.2f}. QUAL's profitability loading has stayed small and was {roll['QUAL'].iloc[-1]:.2f} in the latest "
    f"window, and SIZE's size loading was briefly negative in 2021. An investor buying these funds for a factor needs to "
    f"monitor the exposure, not only the label.")
t9 = ES.copy()
t9 = pd.DataFrame({"Ann. return": t9["Ann. return"].map(pct), "Volatility": t9["Volatility"].map(pct),
                   "Sharpe": t9["Sharpe"].map(f2)})
t9.index.name = "Fund"
r.table(t9, caption=f"Table 8. ETF performance, {rs:%b %Y} – {re_:%b %Y}, against the Fama-French market portfolio.")
r.p(f"Over the same period no ETF had a higher Sharpe ratio than the market portfolio ({ES.loc['Market (Mkt-RF + RF)','Sharpe']:.3f}); "
    f"QUAL ({ES.loc['QUAL','Sharpe']:.3f}) and MTUM ({ES.loc['MTUM','Sharpe']:.3f}) came closest. This is consistent with the weak long-short factor returns of the 2010s and 2020s in Table 2.")

rb = pd.read_csv(D / "B_robust_capm_ff3.csv", index_col=[0, 1])
tr = pd.DataFrame({"Alpha /yr": rb["Alpha (ann.)"].map(pct), "t(α)": rb["t(alpha)"].map(f2),
                   "Market beta": rb["Beta"].map(f2), "R²": rb["R2"].map(f2)})
tr.index = [f"{a} – {b}" for a, b in tr.index]
tr.index.name = "ETF – model"
r.table(tr, caption="Table 9. Robustness: CAPM and Fama-French three-factor regressions (Newey-West t-statistics).", font=7.5)
r.p(f"Under the CAPM and the three-factor model the conclusions hold: no ETF has a significant alpha "
    f"(largest |t| = {rb['t(alpha)'].abs().max():.2f}), and USMV's beta stays well below 1 "
    f"({rb.loc[('USMV','CAPM'),'Beta']:.2f} under the CAPM).")
r.h1("Conclusion")
r.p("Sixty-three years of data support a market, momentum, value, profitability and investment premium, but not a "
    "reliable size premium, and every factor has gone through losing periods of five years or more. The practical "
    "answer to these drawdowns is diversification across factors, which raised the Sharpe ratio of "
    "the best single factor by about half. The iShares factor ETFs do deliver the factor on the label, but in very different doses: "
    "momentum and value funds carry meaningful exposure, while the quality and size funds are close to the market "
    "with a modest tilt, so their names overstate what investors get.")
r.h1("Limitations")
r.bullets([
    "Fama-French factors are paper long-short portfolios before trading costs; investors cannot capture them in full.",
    f"The ETF sample is only {m['n_reg']} months and dominated by one long bull market.",
    "Recession and inflation splits have few observations and low statistical power.",
    "Factor definitions in the ETFs' MSCI indices differ from Fama-French definitions; loadings measure overlap, not intent.",
])
r.h1("References")
r.bullets([
    "Carhart, M. (1997). On Persistence in Mutual Fund Performance. <i>Journal of Finance</i>, 52(1), 57–82.",
    "Fama, E. and French, K. (1993). Common Risk Factors in the Returns on Stocks and Bonds. <i>Journal of Financial "
    "Economics</i>, 33(1), 3–56.",
    "Fama, E. and French, K. (2015). A Five-Factor Asset Pricing Model. <i>Journal of Financial Economics</i>, 116(1), 1–22.",
    "Jegadeesh, N. and Titman, S. (1993). Returns to Buying Winners and Selling Losers. <i>Journal of Finance</i>, 48(1), 65–91.",
    "Newey, W. and West, K. (1987). A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent "
    "Covariance Matrix. <i>Econometrica</i>, 55(3), 703–708.",
    "Kenneth R. French Data Library, mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html.",
])
print("pages:", r.build())
