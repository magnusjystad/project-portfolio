"""Builds report/lazy_prices_sp100.pdf (paper-style, about 10 pages) from the notebook's outputs in data/."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import pandas as pd

from common.report import Report

D, F = ROOT / "data", ROOT / "report" / "figures"
cmw = lambda ws: [w * 28.35 for w in ws]
MAIN = json.load(open(D / "main_result.json"))
QT = pd.read_csv(D / "quintile_stats.csv", index_col=0)
ROB = pd.read_csv(D / "robustness.csv", index_col=0)
SENT = pd.read_csv(D / "sentiment_sorts.csv", index_col=0)
FMR = pd.read_csv(D / "fama_macbeth_raw.csv", index_col=0).fillna("")
FMS = pd.read_csv(D / "fama_macbeth_std.csv", index_col=0).fillna("")
COMP = pd.read_csv(D / "comparison_with_paper.csv", index_col=0)
COV = pd.read_csv(D / "coverage.csv", index_col=0)
SRCC = pd.read_csv(D / "section_sources.csv", index_col=0)
DESC = pd.read_csv(D / "descriptives.csv", index_col=0)
CORR = pd.read_csv(D / "correlations.csv", index_col=0)
TOP = pd.read_csv(D / "largest_changers.csv")
TF = pd.read_csv(D / "text_features.csv")
FB = pd.read_csv(D / "finbert_mda.csv")
CH = pd.read_csv(D / "quintile_characteristics.csv", index_col=0)
YR = pd.read_csv(D / "yearly_spread.csv", index_col=0).iloc[:, 0]
WIN = pd.read_csv(D / "event_time_windows.csv", index_col=0)
per_q = CH.loc["Firms"].mean()
n_firms_valid = pd.read_csv(D / "panel_monthly.csv", usecols=["ticker", "sim_combined"]).dropna()["ticker"].nunique()

pc = lambda x, d=2: f"{x * 100:.{d}f}%"
sig = lambda t: "significant at 5%" if abs(t) >= 1.96 else ("significant at 10%" if abs(t) >= 1.645 else "not significant")
a_m, t_a = MAIN["Alpha FF5+Mom (monthly)"], MAIN["t(alpha)"]
vw = ROB.loc["sim_combined · value-weight"]
n_pairs = int(COV["Usable similarity pairs"].sum())
n_docs = int(COV["10-Ks (original filings)"].sum())
n_sent = int(FB["n_sent"].sum())


def fm_cell(tab, spec, var):
    return tab.loc[var, spec] if var in tab.index and tab.loc[var, spec] != "" else "–"


def fm_parse(tab, spec, var):
    s = fm_cell(tab, spec, var)
    if s == "–":
        return None, None
    c, t = s.split(" (")
    return float(c), float(t.rstrip(")"))


sim_std = fm_parse(FMS, "(2) + controls", "sim_combined")
sim_raw = fm_parse(FMR, "(2) + controls", "sim_combined")
neg3 = fm_parse(FMS, "(3) + tone", "d_lm_negative")
fb3 = fm_parse(FMS, "(3) + tone", "finbert_mda")
sim3 = fm_parse(FMS, "(3) + tone", "sim_combined")

r = Report(ROOT / "report" / "lazy_prices_sp100.pdf", "Lazy Prices in the S&P 100: A Replication with Dictionary and FinBERT Tone",
           "Investment Research Portfolio · Project 15 · 10-K filings FY2012–2025, returns January 2014 – September 2026")

# ---------------------------------------------------------------------------------------------------------------------
r.h1("Abstract")
r.abstract(
    f"Cohen, Malloy and Nguyen (2020) show that US firms which barely change the wording of their annual and quarterly reports "
    f"outperform firms that change them a lot. I repeat their core test on the current S&P 100 using {n_docs:,} original 10-K "
    f"filings for fiscal years 2012–2025. Each firm's Risk Factors (Item 1A) and MD&A (Item 7) are compared with the prior "
    f"year's by cosine similarity. A monthly, equal-weighted portfolio that is long the most similar quintile and short the least "
    f"similar earns {pc(MAIN['Mean (monthly)'])} a month from January 2014 to September 2026 (t = {MAIN['t(mean)']:.2f}; Sharpe "
    f"{MAIN['Sharpe (ann.)']:.2f}). Its Fama-French five-factor plus momentum alpha is {pc(a_m)} a month, or {pc(a_m * 12, 1)} a year "
    f"(t = {t_a:.2f}, {sig(t_a)}). The value-weighted version earns an alpha of {pc(vw['Alpha FF5+Mom (monthly)'])} "
    f"(t = {vw['t(alpha)']:.2f}). In Fama-MacBeth regressions with size, momentum and short-term reversal controls, a one-standard-"
    f"deviation increase in similarity predicts {sim_std[0]:.2f}% higher next-month return (t = {sim_std[1]:.2f}, {sig(sim_std[1])}). "
    f"The equal-weighted direction matches the paper (the value-weighted one does not), but with about {per_q * 5:.0f} large-cap "
    f"firms a month the portfolio test has little power. Loughran-McDonald "
    f"tone changes and FinBERT scores of {n_sent:,} MD&A sentences add little.")

# ---------------------------------------------------------------------------------------------------------------------
r.h1("1. Introduction")
r.p("Cohen, Malloy and Nguyen (2020, <i>Journal of Finance</i>; NBER WP 25084) use every US 10-K and 10-Q filed from 1995 to "
    "2014. They show that when a firm actively changes the language of its reports, the change predicts future earnings, "
    "profitability, news and even bankruptcies, yet there is no announcement effect: returns accrue only when the information is "
    "later revealed, suggesting investors are inattentive. Their main measure is the similarity of a filing's text to the same "
    "filing a year earlier. From 1995 to 2014 the most similar quintile beat the "
    "least similar by 0.31% a month (t = 3.13) equal-weighted, with a five-factor alpha of 0.32% (t = 4.21).")
r.p("This replication asks a narrower question that matters to a practitioner: does the effect show up after the paper's sample "
    "ends, in the largest and most closely followed US companies? Large firms' filings are read by more analysts, which should make "
    "'lazy' pricing less likely. The test also adds two tone measures, the Loughran-McDonald (2011) word lists and FinBERT "
    "(Araci 2019; ProsusAI/finbert), to see whether what a filing says adds to how much it changed.")

# ---------------------------------------------------------------------------------------------------------------------
r.h1("2. Data")
r.p(f"<b>Universe.</b> The 101 current S&P 100 constituents (Wikipedia list, 7 October 2026; Alphabet's two share classes are one "
    f"firm, so 100 firms). <b>Filings.</b> All 10-Ks for fiscal years 2011–2025 were downloaded from SEC EDGAR with the "
    f"<i>edgartools</i> package. For each firm and fiscal year only the original filing is used (amendments are dropped), and "
    f"Item 1A and Item 7 are extracted. When edgartools' parser returns a short or empty item (under 5,000 characters for Item 1A "
    f"or 8,000 for Item 7, typically a cross-reference), the section is taken from the full 10-K text by regular expression or, "
    f"where the 10-K incorporates it by reference, from the Exhibit 13 annual report. <b>Returns.</b> Monthly total returns are "
    f"from yfinance adjusted closes. Market capitalisation = shares outstanding from the XBRL cover page (summed over share classes) "
    f"× month-end close. Fama-French five factors and momentum come from Kenneth French's data library. <b>Dictionary.</b> "
    f"Loughran-McDonald Master Dictionary 1993–2025 (Notre Dame SRAF).")
src = SRCC.copy()
src.columns = ["Item 1A", "Item 7"]
src.index.name = "Section taken from"
r.table(src, caption="Table 1. Where each section's text comes from, all original 10-Ks FY2012–2025.", col_widths=cmw([5.0, 2.5, 2.5]), font=7.5)
r.p(f"<b>Usable pairs.</b> A similarity score is used only if both years' sections come from the 10-K itself, by the same "
    f"extraction route, for consecutive fiscal years. Comparing an Exhibit 13 extract with a 10-K item would measure formatting "
    f"rather than disclosure. This leaves <b>{n_pairs:,} firm-year pairs from {n_firms_valid} "
    f"firms</b>. The largest exclusions are banks that publish MD&A in Exhibit 13, and firms that were not yet public or filed 20-Fs "
    f"early in the sample.")
cv = COV.T.copy()
cv.columns = [str(c) for c in cv.columns]
r.table(cv, caption="Table 2. Coverage by fiscal year.", col_widths=cmw([4.2] + [0.95] * len(cv.columns)), font=6.5)

# ---------------------------------------------------------------------------------------------------------------------
r.h1("3. Method")
r.bullets([
    "<b>Cleaning.</b> Lines with more digits than letters (table rows) are dropped, text is lowercased, only alphabetic tokens are "
    "kept (removing numbers), and English stop words (scikit-learn list) and one-letter tokens are removed.",
    "<b>Similarity.</b> Cosine similarity of word-count vectors between each 10-K and the prior year's, separately for Item 1A, "
    "Item 7 and the two combined (the main signal). A higher value means fewer changes.",
    "<b>Dictionary tone.</b> Share of all words (before stop-word removal) in the Loughran-McDonald negative, uncertainty and "
    "litigious lists, and the year-over-year change in each.",
    f"<b>FinBERT tone.</b> Item 7 is split into sentences of at least five words ({n_sent:,} in total). Each is scored by "
    "ProsusAI/finbert (maximum 256 tokens), and the firm-year score is the mean of P(positive) − P(negative).",
    f"<b>Portfolios.</b> At each month-end from December 2013 to August 2026, every firm carries its most recent usable signal "
    f"filed on or before that date and at most 15 months old. Firms are ranked into similarity quintiles (about {per_q:.0f} stocks each). "
    "The strategy is long Q5 (most similar) and short Q1 (least similar), equal-weighted, rebalanced monthly. Returns run from "
    "January 2014 to September 2026.",
    "<b>Statistics.</b> Mean, Sharpe ratio and t-statistic (Newey-West, 6 lags), and alpha from a regression on the Fama-French "
    "five factors plus momentum.",
    "<b>Fama-MacBeth.</b> Each month, next-month return (%) is regressed cross-sectionally on similarity, the change in the "
    "negative-word share and the FinBERT score, controlling for log market cap, 12-1 month momentum and the prior-month return. "
    "Coefficients are averaged with Newey-West t-statistics. Specification (a) uses raw variables, comparable with the paper's "
    "Table IV. Specification (b) standardises each regressor every month, so each coefficient is the return per one standard "
    "deviation.",
])

# ---------------------------------------------------------------------------------------------------------------------
r.h1("4. Results")
r.h2("4.1 How much do S&P 100 10-Ks change?")
d = DESC.loc[["sim_1a", "sim_7", "sim_combined", "lm_negative", "d_lm_negative", "finbert_mda"],
             ["count", "mean", "std", "1%", "50%", "99%"]].copy()
d.index = ["Similarity, Item 1A", "Similarity, Item 7", "Similarity, combined", "LM negative share", "Δ LM negative share",
           "FinBERT MD&A tone"]
d["count"] = d["count"].map(lambda v: f"{v:,.0f}")
for c in ["mean", "std", "1%", "50%", "99%"]:
    d[c] = d[c].map(lambda v: f"{v:.4f}")
r.table(d, caption="Table 3. Descriptive statistics of the usable pairs. The paper's full-sample cosine similarity has a median "
        "of 0.947 and an SD of 0.191 (Table I, Panel B).", col_widths=cmw([4.5, 1.6, 1.8, 1.8, 1.8, 1.8, 1.8]), font=7.2)
r.image(F / "fig_similarity_by_year.png", 15.0, "Figure 1. Distribution of year-over-year similarity (Items 1A + 7) by fiscal year.")
r.p(f"S&P 100 filings are even more repetitive than the paper's full sample: the median combined similarity is "
    f"{DESC.loc['sim_combined', '50%']:.3f}, and the 1st percentile is {DESC.loc['sim_combined', '1%']:.3f}. Big changes are rare. "
    f"The five lowest scores in the sample are "
    + ", ".join(f"{t.ticker} FY{t.fy} ({t.sim_combined:.2f})" for t in TOP.head(5).itertuples()) + " (the ten lowest are in "
    f"data/largest_changers.csv). Similarity is positively but not strongly related to tone: the Spearman correlation between "
    f"combined similarity and the change in the negative-word share is {CORR.loc['sim_combined', 'd_lm_negative']:.2f}, and with "
    f"FinBERT tone {CORR.loc['sim_combined', 'finbert_mda']:.2f}.")
tp = TOP.copy()
tp["filed"] = tp["filed"].str[:10]
for c in ["sim_1a", "sim_7", "sim_combined"]:
    tp[c] = tp[c].map(lambda v: f"{v:.3f}" if pd.notna(v) else "–")
tp.columns = ["Ticker", "Fiscal year", "Filed", "Similarity 1A", "Similarity 7", "Similarity combined"]
r.table(tp, caption="Table 4. The ten largest year-over-year changes among the usable pairs.", index=False,
        col_widths=cmw([2.0, 2.0, 2.6, 2.6, 2.6, 3.0]), font=7.5)
r.image(F / "fig_tone_by_year.png", 15.0, "Figure 2. Median tone by fiscal year.")

r.h2("4.2 Portfolio test")
qt = QT.loc[["Q1", "Q2", "Q3", "Q4", "Q5", "Q5-Q1"], ["Mean (monthly)", "t(mean)", "Sharpe (ann.)", "Alpha FF5+Mom (monthly)", "t(alpha)"]].copy()
qt.index = ["Q1 (changers)", "Q2", "Q3", "Q4", "Q5 (non-changers)", "Q5 − Q1"]
for c in ["Mean (monthly)", "Alpha FF5+Mom (monthly)"]:
    qt[c] = qt[c].map(lambda v: pc(v))
for c in ["t(mean)", "t(alpha)", "Sharpe (ann.)"]:
    qt[c] = qt[c].map(lambda v: f"{v:.2f}")
qt.columns = ["Excess return / month", "t", "Sharpe (ann.)", "Alpha FF5+Mom / month", "t(alpha)"]
r.table(qt, caption=f"Table 5. Similarity quintile portfolios, equal-weighted, January 2014 – September 2026 ({int(MAIN['Months'])} "
        f"months). Q1–Q5 returns are in excess of the risk-free rate; Q5 − Q1 is a zero-cost spread. Newey-West t-statistics.",
        col_widths=cmw([3.6, 2.6, 1.4, 1.8, 2.8, 1.6]), font=7.5)
r.image(F / "fig_quintile_growth.png", 15.0, "Figure 3. Cumulative returns of the quintile portfolios and the long-short spread.")
r.p(f"The spread is positive, as in the paper: non-changers beat changers by {pc(MAIN['Mean (monthly)'])} a month, or "
    f"{pc(MAIN['Ann. return'], 1)} a year compounded, with an annualised volatility of {pc(MAIN['Ann. vol'], 1)}. But it is "
    f"{sig(MAIN['t(mean)'])} (t = {MAIN['t(mean)']:.2f}). After the six factors, the alpha is {pc(a_m)} a month "
    f"(t = {t_a:.2f}). The factor loadings show what the spread is exposed to: market {MAIN['b_Mkt-RF']:.2f}, size "
    f"{MAIN['b_SMB']:.2f}, value {MAIN['b_HML']:.2f}, profitability {MAIN['b_RMW']:.2f}, investment {MAIN['b_CMA']:.2f}, momentum "
    f"{MAIN['b_Mom']:.2f} (R² {MAIN['R2']:.2f}). Figure 4 shows the alpha of each quintile.")
r.image(F / "fig_quintile_alpha.png", 13.0, "Figure 4. Six-factor alpha by similarity quintile.")
rb = ROB[["Mean (monthly)", "t(mean)", "Sharpe (ann.)", "Alpha FF5+Mom (monthly)", "t(alpha)", "Months"]].copy()
rb.index = [i.replace("sim_combined", "Items 1A + 7").replace("sim_1a", "Item 1A only").replace("sim_7", "Item 7 only") for i in rb.index]
for c in ["Mean (monthly)", "Alpha FF5+Mom (monthly)"]:
    rb[c] = rb[c].map(lambda v: pc(v))
for c in ["t(mean)", "t(alpha)", "Sharpe (ann.)"]:
    rb[c] = rb[c].map(lambda v: f"{v:.2f}")
rb["Months"] = rb["Months"].map(lambda v: f"{v:.0f}")
rb.columns = ["Q5 − Q1 / month", "t", "Sharpe", "Alpha / month", "t(alpha)", "Months"]
r.table(rb, caption="Table 6. Robustness of the long-short spread: section, weighting, sub-period and terciles (about 30 stocks a "
        "side) and a sector-adjusted signal (similarity minus its GICS sector's median each month).",
        col_widths=cmw([5.4, 2.2, 1.2, 1.4, 2.0, 1.4, 1.4]), font=7.5)
r.image(F / "fig_sections.png", 15.0, "Figure 5. Long-short growth of $1 using each section's similarity.")
sa = ROB.loc["sim_combined · sector-adjusted"]
r.p(f"Every quintile has a positive six-factor alpha, from {pc(QT.loc['Q1', 'Alpha FF5+Mom (monthly)'])} (Q1) to "
    f"{pc(QT[['Alpha FF5+Mom (monthly)']].loc[['Q2', 'Q3', 'Q4', 'Q5']].max().iloc[0])} a month. That is the footprint of "
    f"survivorship: today's S&P 100 is, by construction, a list of firms that did well. The long-short spread nets this out, which "
    f"is why it is the right test statistic. The spread comes from Item 1A (Risk Factors), "
    f"{pc(ROB.loc['sim_1a · equal-weight', 'Mean (monthly)'])} a month, while Item 7 alone gives "
    f"{pc(ROB.loc['sim_7 · equal-weight', 'Mean (monthly)'])}. This matches the paper's finding that changes to the risk-factor "
    f"section are especially informative. The result is similar in 2014–2019 and 2020–2026, and the sector-adjusted signal earns "
    f"{pc(sa['Mean (monthly)'])} (t = {sa['t(mean)']:.2f}). "
    + ("None of the variants is significant at 5%." if (ROB["t(mean)"].abs() < 1.96).all()
       else f"{int((ROB['t(mean)'].abs() >= 1.96).sum())} of {len(ROB)} variants are significant at 5%."))
ch = CH.copy()
fmt_ch = {"Firms": "{:.1f}", "Market cap ($bn), median": "{:,.0f}", "Similarity (Items 1A + 7)": "{:.3f}",
          "Δ LM negative share (pp)": "{:.3f}", "FinBERT MD&A tone": "{:.3f}", "Financials share": "{:.0%}",
          "Health Care share": "{:.0%}", "IT share": "{:.0%}"}
ch = pd.DataFrame({c: [fmt_ch[i].format(ch.loc[i, c]) for i in ch.index] for c in ch.columns}, index=ch.index)
ch.index = ["Firms per month", "Market cap ($bn), median", "Similarity (Items 1A + 7)", "Δ LM negative share (pp)",
            "FinBERT MD&A tone", "Financials, share of firms", "Health Care, share of firms", "Information Technology, share of firms"]
r.table(ch, caption="Table 7. Characteristics of the similarity quintiles, averaged over the 153 formation months (compare the "
        "paper's Table III). Sectors are today's GICS sectors (Wikipedia list).", col_widths=cmw([6.0, 2.0, 2.0, 2.0, 2.0, 2.0]), font=7.5)
r.p(f"As in the paper's Table III, where the tone of the changed text is four times as negative in Q1 as in Q5, changers' "
    f"language turns more negative: the negative-word share rises by {CH.loc['Δ LM negative share (pp)', 'Q1']:.3f}pp a year in "
    f"Q1 against {CH.loc['Δ LM negative share (pp)', 'Q5']:.3f}pp in Q5. Unlike the paper, where changers are the larger firms, "
    f"changers here are smaller (median ${CH.loc['Market cap ($bn), median', 'Q1']:,.0f}bn vs "
    f"${CH.loc['Market cap ($bn), median', 'Q5']:,.0f}bn). The sector mix "
    f"differs sharply: {CH.loc['Financials share', 'Q5']:.0%} of non-changers are financials against "
    f"{CH.loc['Financials share', 'Q1']:.0%} of changers, while health care is {CH.loc['Health Care share', 'Q1']:.0%} of "
    f"changers and {CH.loc['Health Care share', 'Q5']:.0%} of non-changers. That is why the sector-adjusted variant matters: it "
    f"gives {pc(ROB.loc['sim_combined · sector-adjusted', 'Mean (monthly)'])} a month against "
    f"{pc(MAIN['Mean (monthly)'])} for the raw signal.")
r.image(F / "fig_yearly_spread.png", 14.5, f"Figure 6. Long-short return by calendar year; positive in {int((YR > 0).sum())} of "
        f"{len(YR)} years.")

r.h2("4.3 Fama-MacBeth regressions")
lab = {"const": "Intercept", "sim_combined": "Similarity (Items 1A + 7)", "d_lm_negative": "Δ LM negative share",
       "finbert_mda": "FinBERT MD&A tone", "log_mcap": "log market cap", "mom_12_1": "Momentum (12-1)", "ret_prev": "Prior-month return"}
for tab, title, cap in [(FMS, "Table 8", "standardised regressors: coefficient = % return per one cross-sectional SD"),
                        (FMR, "Table 9", "raw regressors, comparable with the paper's Table IV (Sim_Cosine 0.31, t = 2.51)")]:
    t_ = tab.copy()
    t_.index = [lab.get(i, i) for i in t_.index]
    r.table(t_, caption=f"{title}. Fama-MacBeth regressions of next-month return (%), {cap}. Newey-West t-statistics in "
            "parentheses.", col_widths=cmw([3.8, 3.3, 3.3, 3.3, 3.3]), font=7.0)
r.p(f"With controls, a one-SD increase in similarity predicts a {sim_std[0]:.2f}% higher next-month return (t = {sim_std[1]:.2f}; "
    f"{sig(sim_std[1])}). In raw units the coefficient is {sim_raw[0]:.2f} (t = {sim_raw[1]:.2f}), against 0.31 in the paper. "
    f"Because S&P 100 similarity varies much less than in the paper (SD {DESC.loc['sim_combined', 'std']:.3f} vs 0.191), the raw "
    f"coefficients are not directly comparable, and the standardised effect is the better comparison: 0.31 × 0.191 ≈ 0.06% a month "
    f"per SD in the paper. Adding tone (specification 3): Δ negative share {neg3[0]:.2f} (t = {neg3[1]:.2f}), FinBERT tone "
    f"{fb3[0]:.2f} (t = {fb3[1]:.2f}), and similarity stays at {sim3[0]:.2f} (t = {sim3[1]:.2f}).")

r.image(F / "fig_fm_rolling.png", 15.0, "Figure 7. Monthly Fama-MacBeth coefficient on standardised similarity (specification 2).")
r.p("The monthly coefficients are noisy, which is typical of Fama-MacBeth estimates with about 75 firms. The average is "
    "positive, and the rolling mean shows how much of it depends on a few periods.")

r.h2("4.4 Do the tone measures sort returns on their own?")
st = SENT[["Mean (monthly)", "t(mean)", "Alpha FF5+Mom (monthly)", "t(alpha)"]].copy()
for c in ["Mean (monthly)", "Alpha FF5+Mom (monthly)"]:
    st[c] = st[c].map(lambda v: pc(v))
for c in ["t(mean)", "t(alpha)"]:
    st[c] = st[c].map(lambda v: f"{v:.2f}")
st.columns = ["Q5 − Q1 / month", "t", "Alpha / month", "t(alpha)"]
r.table(st, caption="Table 10. Long-short quintile spreads sorted on tone, equal-weighted, January 2014 – September 2026.",
        col_widths=cmw([7.0, 2.4, 1.4, 2.4, 1.6]), font=7.5)

r.p(f"Sorted on its own, neither tone measure produces a reliable spread: the largest t-statistic in Table 10 is "
    f"{SENT['t(mean)'].abs().max():.2f}. In the Fama-MacBeth regressions FinBERT tone has a positive but insignificant coefficient, "
    f"and adding both tone measures does not weaken the similarity coefficient. Similarity therefore carries information that "
    f"the level and change of tone do not, as the paper argues.")

r.h2("4.5 Is there an announcement effect?")
wn = WIN.copy()
for c in ["Q5 (non-changers)", "Q1 (changers)", "Q5 − Q1"]:
    wn[c] = wn[c].map(lambda v: pc(v))
wn["t"] = wn["t"].map(lambda v: f"{v:.2f}")
wn["Filings per quintile"] = wn["Filings per quintile"].map(lambda v: f"{v:.0f}")
r.table(wn, caption="Table 11. Cumulative abnormal return (stock minus the equal-weighted sample average) in event-time windows "
        "after the 10-K filing, for filings in the most and least similar quintile of their fiscal-year cohort (filings from 2013). "
        "t-statistics treat filings as independent.", col_widths=cmw([4.2, 2.6, 2.4, 2.0, 1.4, 2.4]), font=7.5)
r.image(F / "fig_event_time.png", 14.5, "Figure 8. Cumulative abnormal return after the filing month, by similarity quintile.")
w0, w13, w46, w712 = (WIN.loc[k] for k in WIN.index)
r.p(f"The paper's most striking claim is that the market does not react when a changed 10-K is filed, and the return gap opens "
    f"later as the news comes out. The S&P 100 data fit that pattern: in the filing month and the next three months changers "
    f"do no worse than non-changers (Q5 − Q1 = {pc(w0['Q5 − Q1'])} and {pc(w13['Q5 − Q1'])}, t = {w0['t']:.2f} and "
    f"{w13['t']:.2f}). The gap opens in months 4–6 ({pc(w46['Q5 − Q1'])}, t = {w46['t']:.2f}) and 7–12 "
    f"({pc(w712['Q5 − Q1'])}, t = {w712['t']:.2f}). With about {int(w0['Filings per quintile'])} filings per quintile and "
    f"overlapping windows, this is suggestive rather than conclusive.")

# ---------------------------------------------------------------------------------------------------------------------
r.h1("5. Comparison with Cohen, Malloy and Nguyen (2020)")
cp = COMP.copy()
cp.index.name = ""
r.table(cp, caption="Table 12. The original paper (NBER WP 25084, March 2019 revision: Table I Panel A/B, Table II Sim_Cosine, Table IV "
        "column 2) and this replication.", col_widths=cmw([5.4, 5.8, 5.8]), font=7.2)
r.p(f"The direction is the same as in the paper: non-changers outperform changers. The size of the effect is in the same range "
    f"({pc(MAIN['Mean (monthly)'])} vs 0.31% a month), but the statistical strength is much weaker. That is what one would expect "
    f"with about {per_q * 5:.0f} firms instead of several thousand, 153 months instead of the paper's 20 years, and a universe of mega-caps. The paper's "
    f"value-weighted result (0.34%, t = 2.53) shows the effect is not confined to small stocks; here the value-weighted spread "
    f"is {pc(vw['Mean (monthly)'])} (t = {vw['t(mean)']:.2f}), the opposite sign, in a universe where a few very large firms "
    f"carry most of the weight.")

# ---------------------------------------------------------------------------------------------------------------------
r.h1("6. Limitations")
r.bullets([
    f"<b>Sample size.</b> About {per_q * 5:.0f} firms with a usable signal each month means about {per_q:.0f} stocks per quintile, "
    f"so each stock is about {1 / per_q:.0%} of its leg, "
    "so the test cannot detect an effect of the paper's size (0.3% a month) with confidence. The original uses all US firms "
    "with EDGAR filings (86,965 10-Ks and 258,271 10-Qs).",
    "<b>Survivorship and look-ahead bias.</b> The universe is today's S&P 100, so firms are included because they became large "
    "and survived to 2026. Earlier members that shrank, were acquired or failed are missing, and some current members were "
    "small in 2014. This biases average returns up and may weaken the changer effect, because the failures that the paper "
    "links to big changes are excluded.",
    "<b>10-K only, once a year.</b> The paper also uses 10-Qs and holds each signal for three months after filing. With 10-Ks "
    "only, the signal is up to a year old, and the portfolio changes little from month to month.",
    "<b>Section extraction.</b> Items are parsed by edgartools, with regex and Exhibit 13 fallbacks. Pairs that mix extraction "
    "routes are excluded rather than corrected, which removes most banks' MD&A. Parsing errors would show up as false 'changers'.",
    "<b>Factor model.</b> Fama-French five factors plus momentum, not the paper's market, size, value, momentum and liquidity "
    "model. The two are similar but not identical.",
    "<b>Tone models.</b> FinBERT was trained on financial news and analyst reports, not 10-Ks, and truncates sentences at 256 "
    "tokens. The Loughran-McDonald lists are counted without the paper's 'sentiment of change' (tone of only the changed text).",
    "<b>Costs.</b> Returns are before trading costs. The long-short portfolio is cheap to trade because signals change once a year.",
])
r.h1("References")
r.p("Araci, D. (2019). FinBERT: Financial sentiment analysis with pre-trained language models. arXiv:1908.10063. · "
    "Cohen, L., Malloy, C. and Nguyen, Q. (2020). Lazy Prices. <i>Journal of Finance</i> 75(3), 1371–1415 (NBER WP 25084). · "
    "Fama, E. and French, K. (2015). A five-factor asset pricing model. <i>Journal of Financial Economics</i> 116(1), 1–22. · "
    "Fama, E. and MacBeth, J. (1973). Risk, return, and equilibrium. <i>Journal of Political Economy</i> 81(3), 607–636. · "
    "Loughran, T. and McDonald, B. (2011). When is a liability not a liability? <i>Journal of Finance</i> 66(1), 35–65.")
r.build()
print("built")
