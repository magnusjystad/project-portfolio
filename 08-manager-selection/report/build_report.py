"""Builds report/dd_report.pdf, report/scorecard.pdf and report/dd_questions.pdf from the outputs of notebooks/selection.ipynb."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import numpy as np
import pandas as pd

from common import data as D
from common.report import Report

DATA, FIG = ROOT / "data", ROOT / "report" / "figures"
rd = lambda n: pd.read_csv(DATA / f"{n}.csv", index_col=0)
PERF, LOAD, PEOPLE, PRICE = rd("performance"), rd("factor_loadings"), rd("people"), rd("price")
PORT, PROC, SC, SECT, REG = rd("portfolio"), rd("process_checks"), rd("scorecard"), rd("sector_weights"), rd("region_weights")
META = json.load(open(DATA / "meta.json"))
FIL = json.load(open(DATA / "nport" / "filings.json"))
FUNDS, ALL = ["ANWPX", "DODWX", "PRGSX"], ["ANWPX", "DODWX", "PRGSX", "ACWI"]
NAMES = {"ANWPX": "Capital Group New Perspective Fund (Class A)", "DODWX": "Dodge &amp; Cox Global Stock Fund (Class I)",
         "PRGSX": "T. Rowe Price Global Stock Fund (Investor Class)", "ACWI": "iShares MSCI ACWI ETF"}
TURNOVER = {"ANWPX": 0.23, "DODWX": 0.26, "PRGSX": 1.722, "ACWI": 0.03}   # prospectus "portfolio turnover rate", latest fiscal year
pct = lambda x, d=1: f"{x * 100:.{d}f}%"
pp = lambda x, d=1: f"{x * 100:+.{d}f}pp"
W = META["weights"]
best, rec = META["best_active"], META["recommend"]

# Rolling 3-year excess (same construction as the notebook) for the latest and extreme values
px = pd.read_csv(DATA / "fund_prices_daily.csv", index_col=0, parse_dates=True)
R = D.monthly_returns(px[ALL]).loc["2016-10":"2026-09"]
g3 = lambda s: (1 + s).rolling(36).apply(np.prod, raw=True) ** (1 / 3)
ROLL = pd.DataFrame({f: g3(R[f]) - g3(R["ACWI"]) for f in FUNDS}).dropna()
assert ROLL.index[-1] == pd.Timestamp("2026-09-30")

# Sensitivity of the decision to the pillar weights
SCHEMES = {"Brief (25/20/20/20/15)": W,
           "Equal (20% each)": {k: 0.2 for k in W},
           "Performance 50%, others 12.5%": {k: (0.5 if k == "Performance" else 0.125) for k in W},
           "No price pillar (renormalised)": {k: (0 if k == "Price" else v / (1 - W["Price"])) for k, v in W.items()}}
sens = []
for name, w in SCHEMES.items():
    s = sum(SC[k] * v for k, v in w.items())
    b = s.drop("ACWI").idxmax()
    ir = PERF.loc[b, "Information ratio"]
    sens.append({"Weighting": name, **{f: f"{s[f]:.2f}" for f in ALL}, "Top active": b, "Its IR": f"{ir:.2f}",
                 "Decision": b if ir >= 0.2 else "ACWI"})
SENS = pd.DataFrame(sens)

# ---------------------------------------------------------------------------------------------------------------------
r = Report(ROOT / "report" / "dd_report.pdf", "Manager Selection: Three Active Global Equity Funds vs. MSCI ACWI",
           "Investment Research Portfolio · Project 9 · Due diligence report · data to 30 September 2026")
r.h1("Recommendation")
r.abstract(
    f"<b>Recommendation: {rec}.</b> We scored New Perspective (ANWPX), Dodge &amp; Cox Global Stock (DODWX) and "
    f"T. Rowe Price Global Stock (PRGSX) against the iShares MSCI ACWI ETF on five pillars weighted 25/20/20/20/15. "
    f"The highest-scoring active fund is {best} ({SC.loc[best, 'Weighted score']:.2f} of 5). It scores well on process "
    f"(its value, contrarian style is clearly visible in the factor loadings and holdings), price and active share "
    f"({pct(PORT.loc[best, 'Active share vs ACWI 31 Jul 2026'], 0)}). But over the ten years to September 2026 it trailed "
    f"ACWI by {pct(-PERF.loc[best, 'Excess vs ACWI (ann.)'], 2)} a year, an information ratio of "
    f"{PERF.loc[best, 'Information ratio']:.2f}. That is below the 0.2 hurdle in the decision rule, so the rule recommends ACWI. "
    f"PRGSX had the best record (IR {PERF.loc['PRGSX', 'Information ratio']:.2f}, six-factor alpha "
    f"{pct(PERF.loc['PRGSX', 'Alpha 6F (ann.)'], 1)}, t = {PERF.loc['PRGSX', 't(alpha)']:.2f}). It ranks second "
    f"because of single-manager key-person risk, a factor profile that only partly matches its stated quality-growth process, "
    f"172% turnover and a higher fee. ANWPX's 5.75% sales load and 0.18 IR put it last. ACWI itself scores "
    f"{SC.loc['ACWI', 'Weighted score']:.2f}, above every active fund, and the decision holds under all four weightings we tested.")

r.h1("1. Mandate, candidates and data")
r.p("The question is whether any of three well-known active global equity funds has earned its fee against a cheap "
    "global index fund, and which one to hold. Every input is public and dated:")
cand = pd.DataFrame({
    "Fund": [NAMES[f] for f in ALL],
    "Net assets": [f"${float(FIL[f]['net_assets']) / 1e9:,.1f}bn ({FIL[f]['rep_pd_date']})" for f in ALL],
    "Expense ratio": [pct(PRICE.loc[f, "Expense ratio"], 2) for f in ALL],
    "Max load": [pct(PRICE.loc[f, "Max front-end sales load"], 2) for f in ALL],
    "Turnover": [pct(TURNOVER[f], 0) for f in ALL],
    "Holdings": [int(PORT.loc[f, "Holdings (equity lines)"]) for f in ALL]}, index=ALL)
r.table(cand, "Table 1. Candidates. Net assets from each fund's latest Form N-PORT; fees and turnover from the latest "
              "summary prospectus (Form 497K) on EDGAR; holdings = equity lines in the N-PORT filing.",
        col_widths=[1.5 * 28.35, 6.3 * 28.35, 3.3 * 28.35, 1.6 * 28.35, 1.4 * 28.35, 1.4 * 28.35, 1.4 * 28.35])
r.bullets([
    "<b>Returns:</b> daily adjusted closes (distributions reinvested) from yfinance, compounded to monthly total returns, "
    f"October 2016 – September 2026 ({len(R)} months). They are net of fund expenses but before sales loads.",
    "<b>Factors:</b> Fama-French Developed 5 Factors and Developed Momentum (Kenneth French Data Library). The library "
    f"currently ends in {pd.Timestamp(META['reg_end']):%B %Y}, so regressions use {len(R) - 1} months.",
    "<b>Holdings:</b> each fund's latest public Form N-PORT on SEC EDGAR (ANWPX and DODWX at 30 June 2026, PRGSX at 31 July "
    "2026), and ACWI's N-PORT at 30 April and 31 July 2026 for active share. Sector and region weights for ACWI come from "
    "the iShares holdings file (31 July 2026), which carries GICS sectors. Fund holdings are classified with GICS by matching "
    "them to the iShares file, with yfinance sectors as a fallback.",
    "<b>Documents:</b> summary prospectuses filed on EDGAR (Form 497K): ANWPX 28 Nov 2025 (and 30 Nov 2020 for the earlier "
    "team), DODWX 1 May 2026 (and 30 Apr 2021), PRGSX 23 Dec 2025 (and 26 Feb 2021), ACWI 28 Nov 2025.",
])

r.h1("2. Pillar 1 — Performance (25%)")
t = pd.DataFrame({
    "Ann. return": [pct(PERF.loc[f, "Ann. return"], 2) for f in ALL],
    "After max load": [pct(PERF.loc[f, "Ann. return after max load"], 2) for f in ALL],
    "Excess vs ACWI": [pct(PERF.loc[f, "Excess vs ACWI (ann.)"], 2) if f != "ACWI" else "–" for f in ALL],
    "Tracking error": [pct(PERF.loc[f, "Tracking error"], 1) if f != "ACWI" else "–" for f in ALL],
    "IR": [f"{PERF.loc[f, 'Information ratio']:.2f}" if f != "ACWI" else "–" for f in ALL],
    "6F alpha (t)": [f"{pct(PERF.loc[f, 'Alpha 6F (ann.)'], 2)} ({PERF.loc[f, 't(alpha)']:.2f})" for f in ALL],
    "Up / down capture": [f"{PERF.loc[f, 'Up-capture'] * 100:.0f} / {PERF.loc[f, 'Down-capture'] * 100:.0f}" for f in ALL],
    "Rolling 3y beating": [pct(PERF.loc[f, "% rolling 3y beating ACWI"], 0) if f != "ACWI" else "–" for f in ALL],
    "Max DD": [pct(PERF.loc[f, "Max drawdown"], 1) for f in ALL],
    "Vol": [pct(PERF.loc[f, "Volatility"], 1) for f in ALL]}, index=ALL)
r.table(t, "Table 2. Ten-year performance, October 2016 – September 2026, monthly data. Excess = difference in annualised "
           "returns. IR = annualised mean monthly excess / tracking error. Alpha from the six-factor regression (Section 3; "
           "Newey-West t, 3 lags). Capture ratios use months when ACWI rose or fell. Max drawdown on month-end values.", font=7.5)
r.image(FIG / "fig_growth.png", 15.5, "Figure 1. Growth of $1 (net of expenses, before sales loads).")
r.p(f"PRGSX is the only fund with a clearly positive record: {pct(PERF.loc['PRGSX', 'Excess vs ACWI (ann.)'], 1)} a year "
    f"ahead of ACWI with an IR of {PERF.loc['PRGSX', 'Information ratio']:.2f}. It achieved this with high up-capture "
    f"({PERF.loc['PRGSX', 'Up-capture'] * 100:.0f}%), not with downside protection: its down-capture is "
    f"{PERF.loc['PRGSX', 'Down-capture'] * 100:.0f}% and its maximum drawdown ({pct(PERF.loc['PRGSX', 'Max drawdown'])}) is "
    f"almost ten points deeper than ACWI's ({pct(PERF.loc['ACWI', 'Max drawdown'])}). ANWPX beat ACWI by "
    f"{pct(PERF.loc['ANWPX', 'Excess vs ACWI (ann.)'], 2)} a year before its sales load. After paying the maximum 5.75% load once, "
    f"its ten-year return falls to {pct(PERF.loc['ANWPX', 'Ann. return after max load'], 2)}, below ACWI. DODWX lagged by "
    f"{pct(-PERF.loc['DODWX', 'Excess vs ACWI (ann.)'], 2)} a year. All three active funds had deeper drawdowns than the index.")
r.image(FIG / "fig_rolling_excess.png", 15.5,
        f"Figure 2. Rolling 3-year annualised excess return vs. ACWI. Latest (Sep 2026): ANWPX {pp(ROLL['ANWPX'].iloc[-1])}, "
        f"DODWX {pp(ROLL['DODWX'].iloc[-1])}, PRGSX {pp(ROLL['PRGSX'].iloc[-1])} a year.")
r.p(f"Results depend heavily on the period. PRGSX's three-year lead peaked at {pp(ROLL['PRGSX'].max())} a year "
    f"({ROLL['PRGSX'].idxmax():%b %Y}) and fell to {pp(ROLL['PRGSX'].min())} ({ROLL['PRGSX'].idxmin():%b %Y}). DODWX went from "
    f"{pp(ROLL['DODWX'].min())} ({ROLL['DODWX'].idxmin():%b %Y}) to {pp(ROLL['DODWX'].max())} ({ROLL['DODWX'].idxmax():%b %Y}). "
    "These swings track the growth-versus-value cycle more than any steady skill, which is why the regression below matters.")

r.h1("3. Factor regressions")
FAC = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]
lt = pd.DataFrame({c: [f"{LOAD.loc[f, c]:.2f} ({LOAD.loc[f, f't({c})']:.1f})" for f in ALL] for c in FAC}, index=ALL)
lt["Alpha (ann.)"] = [f"{pct(PERF.loc[f, 'Alpha 6F (ann.)'], 2)} ({PERF.loc[f, 't(alpha)']:.2f})" for f in ALL]
lt["R²"] = [f"{LOAD.loc[f, 'R2']:.2f}" for f in ALL]
r.table(lt, f"Table 3. Fama-French Developed five-factor + momentum regressions of monthly excess returns (USD), "
            f"October 2016 – {pd.Timestamp(META['reg_end']):%B %Y}. Coefficients with Newey-West t-statistics in brackets.", font=7.5)
r.p(f"No fund has an alpha that is significant at the 5% level. PRGSX comes closest ({pct(PERF.loc['PRGSX', 'Alpha 6F (ann.)'], 2)} a "
    f"year, t = {PERF.loc['PRGSX', 't(alpha)']:.2f}). Its loadings show a fund that leans growth (HML {LOAD.loc['PRGSX', 'HML']:.2f}), "
    f"is tilted toward momentum (Mom {LOAD.loc['PRGSX', 'Mom']:.2f}, t = {LOAD.loc['PRGSX', 't(Mom)']:.1f}), and is strongly "
    f"<i>negative</i> on profitability (RMW {LOAD.loc['PRGSX', 'RMW']:.2f}, t = {LOAD.loc['PRGSX', 't(RMW)']:.1f}) and on "
    f"investment (CMA {LOAD.loc['PRGSX', 'CMA']:.2f}). Stocks with negative RMW and CMA loadings are low-profitability, "
    f"fast-growing firms, not the established high-quality companies the prospectus describes. DODWX is the clearest style fund: "
    f"HML {LOAD.loc['DODWX', 'HML']:.2f} (t = {LOAD.loc['DODWX', 't(HML)']:.1f}) and momentum {LOAD.loc['DODWX', 'Mom']:.2f} "
    f"(t = {LOAD.loc['DODWX', 't(Mom)']:.1f}), a contrarian value book. ANWPX looks like the index with a mild growth tilt "
    f"(R² {LOAD.loc['ANWPX', 'R2']:.2f}). ACWI's alpha of {pct(PERF.loc['ACWI', 'Alpha 6F (ann.)'], 2)} is roughly its fee, as "
    f"expected for an index fund, and its negative SMB loading reflects that the French developed factors exclude emerging markets.")

r.h1("4. Pillar 2 — People (20%)")
pt = PEOPLE.copy()
pt["Average tenure on fund (yrs)"] = pt["Average tenure on fund (yrs)"].map(lambda x: f"{x:.1f}")
pt.columns = ["Named managers", "Avg tenure (yrs)", "Longest (yrs)", "Departures (~5y)", "Departed", "Key-person risk"]
pt["Key-person risk"] = pt["Key-person risk"].map({True: "Yes", False: "No"})
r.table(pt, "Table 4. Portfolio managers named in the latest summary prospectus versus the one about five years earlier. "
            "Tenure is years managing this fund as stated in the prospectus.", font=7.5)
r.bullets([
    "<b>ANWPX</b> uses Capital Group's multi-manager system with ten named managers (seven in November 2020). Robert Lovelace "
    "has managed the fund since 2001. Joanna Jonsson and Jonathan Knowles left the roster; Kohei Higashi and Anne-Marie "
    "Peterson joined in 2021 and Aline Avzaradel in 2025. Sleeves dilute any one departure, which is the design.",
    "<b>DODWX</b> is run by a five-person investment committee (seven in April 2021). Diana Strandberg and Karol Marcin are no "
    "longer listed. The remaining members are long-serving (Voorhis and Beischer 18 years, Kuo 16).",
    "<b>PRGSX</b> has had one portfolio manager, David Eiswert, since 2012. No change, but every decision rests on one person; "
    "the scorecard deducts a point for that key-person risk.",
])

r.h1("5. Pillar 3 — Process (20%)")
r.p("We test whether each fund's factor loadings and holdings match the philosophy stated in its prospectus, with four "
    "yes/no checks per fund defined from that wording.")
for f in FUNDS:
    checks = PROC.loc[f, "Checks"].split("; ")
    r.p(f"<b>{f}</b> — {int(PROC.loc[f, 'Checks passed'])} of 4: " + "; ".join(checks) + ".")
r.bullets([
    "<b>ANWPX</b> (prospectus: growth potential, \"attractively valued companies\", multiple portfolio managers): the growth "
    "lean and diversification are visible. RMW is slightly negative, so the profitability tilt you would expect from large "
    "multinationals does not show up.",
    "<b>DODWX</b> (prospectus: companies that \"appear to be temporarily undervalued\" with \"a favorable outlook for long-term "
    "profit growth\"): every check passes. It has a significant value loading, negative momentum, and a 14-point underweight "
    "in information technology funding overweights in health care and financials.",
    "<b>PRGSX</b> (prospectus: growth style, \"high-quality companies capable of achieving and sustaining above-average, "
    "long-term earnings growth\", large- and mid-cap, \"broadly diversified\"): the growth and large-cap claims hold, but the "
    "growth tilt is not statistically significant and the profitability loading is significantly negative. Turnover of 172% "
    "a year also sits uneasily with a long-term label. The brief describes PRGSX as concentrated, but its prospectus does not, "
    f"and with {int(PORT.loc['PRGSX', 'Holdings (equity lines)'])} holdings and a top-10 weight of "
    f"{pct(PORT.loc['PRGSX', 'Top-10 weight'], 0)} it is not concentrated by usual standards.",
])

r.h1("6. Pillar 4 — Price (20%)")
prt = pd.DataFrame({"Expense ratio": [pct(PRICE.loc[f, "Expense ratio"], 2) for f in ALL],
                    "Max sales load": [pct(PRICE.loc[f, "Max front-end sales load"], 2) for f in ALL],
                    "All-in (load over 10y)": [pct(PRICE.loc[f, "All-in annual cost (load over 10y)"], 3) for f in ALL],
                    "Gap vs ACWI": [pct(PRICE.loc[f, "Cost gap vs ACWI"], 3) for f in ALL],
                    "Source": PRICE["Source"].values}, index=ALL)
r.table(prt, "Table 5. Costs from each summary prospectus fee table. The sales load is spread evenly over a ten-year holding "
             "period for comparison.")
r.p(f"ACWI costs 0.32% a year. For an investor paying the full sales load, ANWPX Class A costs about {pct(PRICE.loc['ANWPX', 'Cost gap vs ACWI'], 2)} "
    "a year more over ten years, roughly its entire pre-load excess return. Institutional or fee-based investors may get "
    "load-waived or cheaper share classes, which would change this pillar. We score the share classes named in the brief. "
    "PRGSX's Investor Class costs 0.49pp more than ACWI and DODWX's Class I 0.30pp more.")

r.h1("7. Pillar 5 — Portfolio (15%)")
pot = pd.DataFrame({"Holdings date": PORT["Holdings date"],
                    "Active share (Jul 2026 ACWI)": [pct(x, 0) for x in PORT["Active share vs ACWI 31 Jul 2026"]],
                    "Active share (Apr 2026 ACWI)": [pct(x, 0) for x in PORT["Active share vs ACWI 30 Apr 2026"]],
                    "Top-10 weight": [pct(x, 0) for x in PORT["Top-10 weight"]],
                    "Unlisted (Level 3)": [pct(x, 1) for x in PORT["Level 3 (unlisted) weight"]],
                    "US weight": [pct(REG.loc["United States", f], 0) for f in ALL],
                    "EM weight": [pct(REG.loc["Emerging markets", f], 0) for f in ALL]}, index=ALL)
r.table(pot, "Table 6. Portfolio characteristics. Active share = ½ Σ|w_fund − w_ACWI| over equity positions matched by ISIN, "
             "from N-PORT filings. ACWI against itself at the earlier date shows how much three months of index drift "
             "alone contributes (7%). Level 3 = fair-value hierarchy level 3 in N-PORT (no observable price).", font=7.5)
r.image(FIG / "fig_tilts.png", 16.5, "Figure 3. Sector (GICS) and region weights minus ACWI's (percentage points). Fund region = "
                                     "issuer country in N-PORT; ACWI region = iShares 'Location'.")
r.p(f"DODWX is the most different from the index ({pct(PORT.loc['DODWX', 'Active share vs ACWI 31 Jul 2026'], 0)} active share): "
    f"information technology {pp(SECT.loc['Information Technology', 'DODWX'] - SECT.loc['Information Technology', 'ACWI'], 0)}, "
    f"health care {pp(SECT.loc['Health Care', 'DODWX'] - SECT.loc['Health Care', 'ACWI'], 0)}, financials "
    f"{pp(SECT.loc['Financials', 'DODWX'] - SECT.loc['Financials', 'ACWI'], 0)}, and emerging markets "
    f"{pp(REG.loc['Emerging markets', 'DODWX'] - REG.loc['Emerging markets', 'ACWI'], 0)}. PRGSX is a technology fund in "
    f"global clothing (IT {pct(SECT.loc['Information Technology', 'PRGSX'], 0)} vs. {pct(SECT.loc['Information Technology', 'ACWI'], 0)} "
    f"for ACWI). It also holds {pct(PORT.loc['PRGSX', 'Level 3 (unlisted) weight'], 1)} in unlisted, Level 3 positions, mostly private "
    "AI and software companies (Databricks, Anthropic, OpenAI, SambaNova, Waymo, Epic Games). These are valued by the adviser, "
    "not the market. ANWPX, at 60% active share, is the closest to the index. All three funds are underweight the US by 5–10 "
    "points and overweight Europe by 6–11 points. Checking the matching method: an issuer-level match by LEI instead of ISIN "
    "gives active shares of 60%, 83% and 68%, so DODWX stays above the 80% band and no score changes.")

r.h1("8. Scorecard and decision")
r.image(FIG / "fig_scorecard.png", 14.5, "Figure 4. Pillar scores (1–5) and weighted totals.")
sct = SC.copy()
sct = sct.map(lambda x: f"{x:.2f}")
r.table(sct, "Table 7. Scorecard. Scoring rules (fixed before results were viewed, notebook Section 'Scorecard'): performance = "
             "mean of four banded sub-scores (excess return, IR, rolling 3-year hit rate, drawdown vs ACWI); people = tenure "
             "band minus 1 for two or more departures and minus 1 for a single manager; process = checks passed; price = "
             "all-in cost gap band; portfolio = active-share band minus 1 if top-10 &gt; 50%. ACWI is fixed at 3 on performance "
             "and portfolio (it is the benchmark) and 5 on people and process.")
r.p(f"<b>Decision rule</b> (from the brief): recommend the fund with the highest weighted score unless its ten-year IR against "
    f"ACWI is below 0.2; then recommend ACWI. The highest-scoring active fund is {best} at "
    f"{SC.loc[best, 'Weighted score']:.2f}, with an IR of {PERF.loc[best, 'Information ratio']:.2f}. <b>Decision: {rec}.</b>")
r.table(SENS.set_index("Weighting"), "Table 8. Sensitivity of the decision to the pillar weights. Under performance-heavy "
                                     "weighting PRGSX becomes the top active fund and clears the 0.2 IR hurdle, so the "
                                     "rule would pick it. ACWI's own score is still higher.", font=7.5)
r.p("The recommendation depends on the weighting scheme only in the performance-heavy case. There, the rule picks PRGSX, "
    "which is also the only fund with an IR above 0.2. An investor who wants an active global sleeve should look at PRGSX, "
    "subject to the questions on key-person risk, private holdings and turnover in the appendix. The base case, and the "
    "weighting set in advance, is ACWI. It is cheaper, more diversified and has no manager risk, and none of the three "
    "funds has an alpha distinguishable from zero after accounting for factor exposure.")

r.h1("9. Limitations")
r.bullets([
    "Ten years is short for judging skill: with PRGSX's 6.7% tracking error, an IR of 0.53 has a standard error of about "
    "0.32 (1/√10), so even the best record is only about 1.7 standard errors from zero.",
    "One share class per fund, as in the brief. Cheaper classes (e.g., ANWPX F-2/R6, PRGSX I) would raise price scores and "
    "returns. Returns before sales loads are used for everything except the load-adjusted return.",
    "Holdings are one snapshot. ACWI's N-PORT is public only for April and July (its fiscal quarter ends), not for 30 June, "
    "so ANWPX and DODWX are compared with ACWI one month later and three months earlier. The two give the same answer to "
    "within one point. N-PORT is published with a 60-day lag.",
    "PRGSX's unlisted holdings have no ISIN and cannot be in ACWI, so they count fully as active. Depositary receipts and "
    "local lines of the same company have different ISINs; the LEI check in Section 7 shows this moves active share by at "
    "most two points.",
    "Fund region uses the issuer's legal country from N-PORT, while ACWI uses iShares' 'Location'. Companies domiciled in Ireland "
    "or the Netherlands but listed in the US may land in different regions.",
    "Process checks reduce a prospectus to four testable statements; ANWPX's \"attractively valued\" and DODWX's committee "
    "process cannot be tested from returns or holdings.",
    "People data come only from the prospectus roster. It does not capture analyst turnover, manager investment in the fund "
    "or compensation, which is why those are in the meeting questions.",
])

# ---------------------------------------------------------------------------------------------------------------------
s = Report(ROOT / "report" / "scorecard.pdf", "Scorecard: Global Equity Manager Selection",
           f"Project 9 · four options · data to 30 September 2026 · decision: {rec}")
rows = {
    "Weighted score (of 5)": [f"<b>{SC.loc[f, 'Weighted score']:.2f}</b>" for f in ALL],
    "Performance (25%)": [f"{SC.loc[f, 'Performance']:.2f}" for f in ALL],
    "– 10y ann. return": [pct(PERF.loc[f, "Ann. return"], 2) for f in ALL],
    "– Excess vs ACWI / IR": [f"{pct(PERF.loc[f, 'Excess vs ACWI (ann.)'], 2)} / {PERF.loc[f, 'Information ratio']:.2f}" if f != "ACWI" else "–" for f in ALL],
    "– 6F alpha (t)": [f"{pct(PERF.loc[f, 'Alpha 6F (ann.)'], 2)} ({PERF.loc[f, 't(alpha)']:.2f})" for f in ALL],
    "– Up / down capture": [f"{PERF.loc[f, 'Up-capture'] * 100:.0f}% / {PERF.loc[f, 'Down-capture'] * 100:.0f}%" for f in ALL],
    "– Rolling 3y periods beating ACWI": [pct(PERF.loc[f, "% rolling 3y beating ACWI"], 0) if f != "ACWI" else "–" for f in ALL],
    "– Max drawdown": [pct(PERF.loc[f, "Max drawdown"], 1) for f in ALL],
    "People (20%)": [f"{SC.loc[f, 'People']:.0f}" for f in ALL],
    "– Managers / avg tenure": [f"{int(PEOPLE.loc[f, 'Team size (named managers)'])} / {PEOPLE.loc[f, 'Average tenure on fund (yrs)']:.1f}y" if f != "ACWI" else "index" for f in ALL],
    "– Departures (~5y)": [str(int(PEOPLE.loc[f, "Departures in ~5 years"])) if f != "ACWI" else "–" for f in ALL],
    "Process (20%)": [f"{SC.loc[f, 'Process']:.0f}" for f in ALL],
    "– Checks passed": [f"{int(PROC.loc[f, 'Checks passed'])} of 4" if f != "ACWI" else "tracks index" for f in ALL],
    "– Turnover": [pct(TURNOVER[f], 0) for f in ALL],
    "Price (20%)": [f"{SC.loc[f, 'Price']:.0f}" for f in ALL],
    "– Expense ratio / max load": [f"{pct(PRICE.loc[f, 'Expense ratio'], 2)} / {pct(PRICE.loc[f, 'Max front-end sales load'], 2)}" for f in ALL],
    "Portfolio (15%)": [f"{SC.loc[f, 'Portfolio']:.0f}" for f in ALL],
    "– Active share / top-10": [f"{pct(PORT.loc[f, 'Active share vs ACWI 31 Jul 2026'], 0)} / {pct(PORT.loc[f, 'Top-10 weight'], 0)}" for f in ALL],
    "– IT / US weight": [f"{pct(SECT.loc['Information Technology', f], 0)} / {pct(REG.loc['United States', f], 0)}" for f in ALL],
    "– Unlisted (Level 3)": [pct(PORT.loc[f, "Level 3 (unlisted) weight"], 1) for f in ALL],
}
card = pd.DataFrame(rows, index=ALL).T
card.index.name = "Measure"
s.table(card, None, col_widths=[5.4 * 28.35, 2.9 * 28.35, 2.9 * 28.35, 2.9 * 28.35, 2.9 * 28.35], font=8)
s.p(f"<b>Decision rule:</b> highest weighted score among active funds = {best} ({SC.loc[best, 'Weighted score']:.2f}); its "
    f"10-year IR is {PERF.loc[best, 'Information ratio']:.2f} &lt; 0.2, so the recommendation is <b>{rec}</b>. "
    f"Runner-up PRGSX has the only IR above 0.2 ({PERF.loc['PRGSX', 'Information ratio']:.2f}) but scores lower on people "
    "(single manager), process and price.")
s.p("Returns: yfinance total returns, Oct 2016 – Sep 2026. Factors: Kenneth French Developed 5 + Momentum (to "
    f"{pd.Timestamp(META['reg_end']):%b %Y}). Holdings: SEC Form N-PORT; iShares ACWI holdings file. Fees, turnover, managers: "
    "summary prospectuses (Form 497K). Scoring rules: dd_report.pdf, Table 7.")
print("scorecard.pdf pages:", s.build())

# ---------------------------------------------------------------------------------------------------------------------
QUESTIONS = {
    "ANWPX": [
        "Joanna Jonsson and Jonathan Knowles have left the roster since 2020, and three managers joined in 2021–2025. How "
        "was their capital reassigned, and how do you decide how much each of the ten sleeves runs?",
        "With ten independent sleeves, the fund's active share against ACWI is about 60% and its tracking error 3.7%. What "
        "stops the combined portfolio from drifting towards the index, and do you monitor overlap between sleeves?",
        "The prospectus says you buy \"attractively valued\" companies, yet the fund's value (HML) loading is −0.17 (t = −3.5). "
        "How do you define attractive valuation in practice?",
        "Your rolling 3-year excess return against ACWI has been mostly negative since mid-2023. What explains that "
        "period, and what did you change, if anything?",
        "How do you measure a company's exposure to global trade and multinational revenue, which is the fund's founding "
        "idea, and how much of the portfolio meets that test today?",
        "The fund is 11 points overweight Europe and 9 underweight the US. Is this the sum of bottom-up decisions or a view, "
        "and who owns the aggregate country risk?",
        "The Class A shares carry a 5.75% load. Which share classes could we use, at what expense ratio, and what minimums?",
        "With about $170bn in the fund, where does size constrain you (smaller companies, emerging markets, trading costs)?",
        "How is each manager paid: on the sleeve's results, the fund's, or Capital Group's? Over what horizon?",
        "How much do the named managers have invested in this fund (the SAI ownership ranges), and has that changed?",
    ],
    "DODWX": [
        "Diana Strandberg and Karol Marcin are no longer on the committee, which shrank from seven to five. How did "
        "decision-making change, and who now leads the global portfolio?",
        "Over ten years the fund lagged ACWI by 1.3% a year (IR −0.09), and its three-year excess is currently −6.7% a year. "
        "What has to happen for the portfolio to recover that gap, and over what horizon would you accept being judged?",
        "The fund's momentum loading is −0.18 (t = −3.9): you systematically buy recent losers. How do you tell a temporarily "
        "undervalued company from a value trap, and can you show two examples of each?",
        "You are 14 points underweight technology and 12 points overweight health care. Are these deliberate sector views "
        "or the residue of stock picks, and what is the largest loss you would tolerate from them?",
        "Emerging markets are 17% of the fund versus 11% in ACWI. How do you assess governance and state-ownership risk?",
        "Japan is 4 points underweight. Why, given the corporate-governance reforms there?",
        "The prospectus allows currency forwards and swaps, equity options and total return swaps. How much were they used "
        "last year, and what is the hedging policy?",
        "The fund's maximum drawdown (−31%) was deeper than ACWI's (−26%). What portfolio-level risk limits apply?",
        "How does the committee resolve disagreements? Does any member have a veto, and how do you guard against groupthink?",
        "How much of this strategy does Dodge &amp; Cox run across all vehicles, and how do committee members invest in it?",
    ],
    "PRGSX": [
        "You have been sole portfolio manager since 2012. What is the succession plan, who is the named backup, and would "
        "the process survive your departure?",
        "Portfolio turnover was 172% last year. How does that fit with a long-term growth philosophy, and what did trading "
        "cost the fund?",
        "4.9% of the fund is in unlisted Level 3 positions (Databricks, Anthropic, OpenAI, SambaNova, Waymo and others). What "
        "is the limit on private holdings, who values them and how often, and how would you meet heavy redemptions?",
        "The prospectus emphasises \"high-quality companies\", but the fund's profitability (RMW) loading is −0.43 (t = −3.1). "
        "How do you define quality, and why does the portfolio load on low-profitability stocks?",
        "Technology is 44% of the fund versus 30% for ACWI. What is the fund's total exposure to the AI theme, counting "
        "listed and private holdings, and how do you size correlated positions?",
        "Your three-year excess return ranged from +15% a year (to December 2020) to −6% (to December 2023). Which decisions caused each, and what "
        "did you learn from the drawdown?",
        "The momentum loading is +0.14 (t = 2.1). Is momentum part of the process or a by-product?",
        "Down-capture is 103% and the maximum drawdown −35% versus −26% for ACWI. Does the fund have any downside "
        "risk control, and should investors expect that profile to continue?",
        "How large can the strategy grow before capacity hurts results, particularly in private deals and mid-caps?",
        "Is an institutional share class available below the Investor Class's 0.81%, and how much do you have invested "
        "in the fund yourself?",
    ],
}
q = Report(ROOT / "report" / "dd_questions.pdf", "Due Diligence Meeting Questions",
           "Project 9 · ten questions for each portfolio manager, each tied to evidence in the due diligence report")
for f, qs in QUESTIONS.items():
    assert len(qs) == 10
    q.h1(NAMES[f])
    for i, text in enumerate(qs, 1):
        q.p(f"<b>{i}.</b> {text}")
print("dd_questions.pdf pages:", q.build())

# Appendix to the main report: top-10 holdings and meeting questions
r.h1("Appendix A. Ten largest holdings")
HD = {"ANWPX": "2026-06-30", "DODWX": "2026-06-30", "PRGSX": "2026-07-31", "ACWI": "2026-07-31"}
for f, d in HD.items():
    x = pd.read_csv(DATA / "nport" / f"{f}_{d}.csv")
    x = x[x["asset_cat"].isin(["EC", "EP"])]
    top = x.groupby(x["name"].str.title())["pct_val"].sum().sort_values(ascending=False).head(10)
    tt = pd.DataFrame({"Holding": top.index, "Weight": [f"{v:.2f}%" for v in top.values]})
    r.table(tt, f"Table A{list(HD).index(f) + 1}. {NAMES[f]}: ten largest equity positions, % of net assets, Form N-PORT at {d}.",
            index=False, col_widths=[9 * 28.35, 2.5 * 28.35], font=7.5)
r.pagebreak()
r.h1("Appendix B. Questions for each portfolio manager")
for f, qs in QUESTIONS.items():
    r.h2(NAMES[f])
    for i, text in enumerate(qs, 1):
        r.p(f"<b>{i}.</b> {text}")
print("dd_report.pdf pages:", r.build())
