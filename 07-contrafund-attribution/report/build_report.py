"""Builds report/report.pdf from the outputs of notebooks/attribution.ipynb."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import pandas as pd

from common.report import Report

D, F = ROOT / "data", ROOT / "report" / "figures"
rd = lambda n: pd.read_csv(D / f"{n}.csv", index_col=0)
m = json.load(open(D / "meta.json"))
REG, REL, LINK, RES = rd("regressions"), rd("relative_stats").iloc[:, 0], rd("brinson_2025_linked"), rd("residual_2025").iloc[:, 0]
TOP, BOT, QR = rd("top10_contributors"), rd("top10_detractors"), rd("quarterly_returns_bh")
COV = pd.read_csv(D / "coverage.csv")
filings = json.load(open(D / "nport" / "filings.json"))
pct = lambda x, d=2: f"{x * 100:.{d}f}%"
bp = lambda x: f"{x * 1e4:+.0f}"
E = m["effects"]
a6, t6 = m["alpha6"], m["t6"]

r = Report(ROOT / "report" / "report.pdf", "Skill or Exposure? Performance Attribution of Fidelity Contrafund",
           "Investment Research Portfolio · Project 8 · Returns-based 2011–2026 and holdings-based (Brinson-Fachler) 2025")
r.h1("Summary")
r.abstract(
    f"Fidelity Contrafund (FCNTX) returned {pct(REL['FCNTX ann. return'],1)} a year from October 2011 to September 2026, "
    f"{pct(REL['Excess return (ann., geometric)'],1)} a year more than the S&amp;P 500 (IVV), with a {pct(REL['Tracking error'],1)} "
    f"tracking error and an information ratio of {REL['Information ratio']:.2f}. Once its factor exposures are accounted for, the "
    f"evidence for skill is weak: the alpha from a Fama-French five-factor plus momentum regression is {pct(a6)} a year with a "
    f"t-statistic of {t6:.2f}. The fund is a large-cap growth portfolio (negative size, value and investment loadings) with a "
    f"momentum tilt. In calendar year 2025 the fund beat IVV by {pct(m['Rp_act']-m['Rb_act'])} "
    f"({pct(m['Rp_act'])} vs. {pct(m['Rb_act'])}). A holdings-based Brinson-Fachler attribution from the fund's quarterly "
    f"N-PORT filings explains a buy-and-hold excess of {pct(m['Rp_bh']-m['Rb_bh'])}: selection {bp(E['Selection'])} bp, "
    f"allocation {bp(E['Allocation'])} bp and interaction {bp(E['Interaction'])} bp. The fund's private stake in SpaceX was "
    f"its single largest contributor. Under the rule set in advance (skill only if six-factor alpha is positive with t &gt; 2 "
    f"and selection is the largest Brinson effect), the verdict is <b>{m['verdict']}</b>: 2025's selection was real, but "
    f"fifteen years of returns do not show statistically reliable alpha.")

r.h1("1. Data")
r.bullets([
    f"<b>Returns:</b> FCNTX and IVV daily adjusted closes (distributions reinvested) from yfinance, converted to monthly total "
    f"returns, October 2011 – September 2026. Factor regressions end in {pd.Timestamp(m['reg_end']):%B %Y}, the latest month in the "
    f"Kenneth French Data Library (Fama/French 5 Factors 2x3 and Momentum).",
    "<b>Holdings:</b> Form N-PORT-P filings on SEC EDGAR for Fidelity Contrafund (series S000006037) and iShares Core S&amp;P 500 "
    "ETF (series S000004310) at 31 Dec 2024, 31 Mar, 30 Jun and 30 Sep 2025, plus Contrafund's 31 Dec 2025 filing to value private "
    "holdings over the fourth quarter. Net assets: " + ", ".join(
        f"FCNTX {d} ${float(filings['FCNTX'][d]['net_assets'])/1e9:.0f}bn" for d in ["2024-12-31", "2025-09-30"]) + ".",
    "<b>Security returns:</b> holdings identified by ISIN, mapped to exchange tickers with OpenFIGI (with manual tickers for a "
    "few unmapped names, listed in data/manual_ticker_overrides.json) and priced with yfinance total-return closes in USD. "
    "Holdings with no market price (mainly private companies such as SpaceX) are valued with the fund's own fair values per "
    "unit from consecutive N-PORT filings. Cash and money-market funds earn the 3-month T-bill (FRED TB3MS).",
    "<b>Sectors:</b> the yfinance sector field for every stock, applied identically to both portfolios. Private holdings form "
    "their own bucket; the benchmark has none.",
    "<b>Fees:</b> total annual operating expenses of 0.74% for fiscal 2025 (management fee 0.73%, performance-adjusted, plus "
    "0.01% other), from the summary prospectus filed on EDGAR on 27 February 2026.",
])

r.h1("2. Part A — returns-based analysis, 2011–2026")
t = pd.DataFrame({
    "Alpha /yr": REG["Alpha (ann.)"].map(pct), "t(α)": REG["t(alpha)"].map(lambda x: f"{x:.2f}"),
    **{c: [("" if pd.isna(b) else f"{b:.2f} ({tt:.1f})") for b, tt in zip(REG[c], REG[f"t({c})"])]
       for c in ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]},
    "R²": REG["R2"].map(lambda x: f"{x:.2f}")})
t.index.name = "Model"
r.table(t, caption=f"Table 1. Regressions of FCNTX monthly excess returns, {pd.Timestamp(m['reg_start']):%b %Y} – "
        f"{pd.Timestamp(m['reg_end']):%b %Y} ({m['n_reg']} months); Newey-West t-statistics (3 lags) in brackets. As a check, "
        f"the same six-factor model gives IVV an alpha of {pct(m['ivv_alpha6'])} and a market beta of {m['ivv_beta6']:.3f}.",
        font=7.3)
r.p(f"The CAPM alpha of {pct(REG.loc['CAPM','Alpha (ann.)'])} a year shrinks to {pct(a6)} once size, value, profitability, "
    f"investment and momentum are included, and none of the alphas is statistically significant. The loadings describe a "
    f"large-cap (SMB {REG.loc['FF5 + Mom','SMB']:.2f}) growth (HML {REG.loc['FF5 + Mom','HML']:.2f}, CMA "
    f"{REG.loc['FF5 + Mom','CMA']:.2f}) portfolio with a momentum tilt (Mom {REG.loc['FF5 + Mom','Mom']:.2f}, t = "
    f"{REG.loc['FF5 + Mom','t(Mom)']:.1f}). These are exposures an investor could buy cheaply through factor or growth indices.")
rel = pd.DataFrame({"Value": [pct(REL['FCNTX ann. return']), pct(REL['IVV ann. return']), pct(REL['Excess return (ann., geometric)']),
                              pct(REL['Tracking error']), f"{REL['Information ratio']:.2f}", f"{REL['Up-capture']*100:.0f}%",
                              f"{REL['Down-capture']*100:.0f}%"]},
                   index=["FCNTX annualized return", "IVV annualized return", "Excess return (geometric)", "Tracking error",
                          "Information ratio", f"Up-capture ({int(REL['Up months'])} up months)",
                          f"Down-capture ({int(REL['Down months'])} down months)"])
rel.index.name = "Oct 2011 – Sep 2026"
r.table(rel, caption="Table 2. Relative performance vs. IVV.", col_widths=[200, 100])
r.p(f"Contrafund captured {REL['Up-capture']*100:.0f}% of IVV's gains in up months and {REL['Down-capture']*100:.0f}% of its "
    f"losses in down months, an asymmetric profile that produced the excess return. Rolling 36-month six-factor alphas (Figure 1) "
    f"swing between about −2% and +6% a year and were highest in 2024–2026, when the fund's concentrated technology and private "
    f"holdings paid off.")
r.image(F / "fig_rolling_alpha_beta.png", 16.5, "Figure 1. Rolling 36-month alpha (six-factor and CAPM) and market beta.")

r.h1("3. Part B — holdings-based attribution for 2025")
r.h2("3.1 Method")
r.p("For each quarter of 2025 I hold the starting N-PORT holdings of both portfolios unchanged and value them at the end "
    "of the quarter. Sector returns are value-weighted returns of the holdings in each sector. The Brinson-Fachler (1985) "
    "decomposition splits the excess return in each sector into <b>allocation</b> (w<sub>p</sub> − w<sub>b</sub>)(R<sub>b,s</sub> − R<sub>b</sub>), "
    "<b>selection</b> w<sub>b</sub>(R<sub>p,s</sub> − R<sub>b,s</sub>) and <b>interaction</b> (w<sub>p</sub> − w<sub>b</sub>)(R<sub>p,s</sub> − R<sub>b,s</sub>). "
    "The four quarterly results are linked into a 2025 total with Cariño's (1999) logarithmic smoothing, which makes the "
    "effects add up exactly to the annual excess return.")
cov = COV.pivot(index="Quarter", columns="Portfolio")
ct = pd.DataFrame({f"{p}: {c}": cov[(c, p)].map(lambda x: pct(x, 1)) for p in ["FCNTX", "IVV"]
                   for c in ["market price", "N-PORT fair value", "T-bill (cash)", "no price"] if (c, p) in cov.columns})
ct.index = [f"Q{i + 1} 2025" for i in range(len(ct))]
ct.index.name = "Quarter"
r.table(ct, caption="Table 3. Share of each portfolio's starting value by valuation source. 'No price' holdings (acquired or "
        "delisted companies without a Yahoo price history) are left out and the remaining weights rescaled.", font=6.8)
r.p(f"Buy-and-hold reproduces IVV's actual 2025 return closely ({pct(RES['IVV buy-and-hold estimate'])} vs. "
    f"{pct(RES['IVV actual 2025 (total return)'])}), which validates the price data and the method.")
r.h2("3.2 Results")
lk = LINK.copy()
lk["Total"] = lk.sum(axis=1)
lk = lk.sort_values("Total", ascending=False)
lk.loc["Total"] = lk.sum()
lt = lk.map(lambda x: bp(x))
lt.index.name = "Sector"
r.table(lt, caption="Table 4. Brinson-Fachler attribution by sector, 2025, Cariño-linked, basis points of excess return.", font=7.5)
r.image(F / "fig_waterfall.png", 15.5, "Figure 2. From IVV's 2025 return to Contrafund's.")
r.p(f"<b>Selection is the largest effect</b> ({bp(E['Selection'])} bp), driven by technology ("
    f"{bp(LINK.loc['Technology','Selection'])} bp), industrials ({bp(LINK.loc['Industrials','Selection'])} bp) and utilities "
    f"({bp(LINK.loc['Utilities','Selection'])} bp). <b>Allocation</b> added {bp(E['Allocation'])} bp, mostly from the "
    f"overweight in communication services ({bp(LINK.loc['Communication Services','Allocation'])} bp). <b>Interaction</b> was "
    f"{bp(E['Interaction'])} bp: positive in private companies (+{LINK.loc['Private / unlisted','Interaction']*1e4:.0f} bp, a "
    f"sector the benchmark does not hold) and negative where the fund was overweight a sector but owned its weaker names, "
    f"notably communication services ({bp(LINK.loc['Communication Services','Interaction'])} bp: Meta, the fund's largest holding, "
    f"returned 13% in 2025 against 66% for Alphabet).")
r.image(F / "fig_attribution_sector.png", 15.5, "Figure 3. Attribution effects by sector.")
r.h2("3.3 The residual: fees and trading")
rs = pd.DataFrame({"2025": [pct(RES['FCNTX actual 2025 (total return)']), pct(RES['FCNTX buy-and-hold estimate']),
                            pct(RES['Residual (actual - estimate)']), pct(RES['of which fees (prospectus expense ratio)']),
                            pct(RES['of which intra-quarter trading and other'])]},
                  index=["FCNTX actual total return", "Buy-and-hold estimate", "Residual", "  of which fees (0.74% expense ratio)",
                         "  of which intra-quarter trading and other"])
rs.index.name = "Item"
r.table(rs, caption="Table 5. Reconciling the buy-and-hold estimate with the fund's actual return.", col_widths=[220, 90])
r.p(f"The actual return was {pct(-RES['Residual (actual - estimate)'])} below the buy-and-hold estimate. Fees explain "
    f"0.74 points. The remaining {pct(-RES['of which intra-quarter trading and other'])} reflects trades within quarters, "
    f"securities lending, cash flows and holdings left out for lack of prices. That is consistent with intra-quarter "
    f"trading adding little or nothing in 2025, though the figure mixes several effects.")
r.h2("3.4 Top contributors and detractors")
fmt = lambda d: pd.DataFrame({"Contribution": d["Contribution"].map(bp), "Avg. active weight": d["Avg_active_weight"].map(lambda x: pct(x, 1))},
                             index=d.index)
tp, bt = fmt(TOP), fmt(BOT)
tp.index.name = bt.index.name = "Issuer"
r.table(tp, caption="Table 6. Ten largest contributors to 2025 excess return (bp). Contribution = Σ quarters of (active weight × "
        "(stock return − benchmark return)), Cariño-linked; share classes of the same issuer are combined.", font=7.5)
r.table(bt, caption="Table 7. Ten largest detractors (bp).", font=7.5)
r.p(f"SpaceX, held through private preferred shares valued by Fidelity, contributed {bp(TOP.iloc[0,0])} bp, more than any "
    f"listed stock. Amphenol was the best listed contributor. The detractors show the cost of concentration: a large "
    f"overweight in Berkshire Hathaway, which returned 11% against 18% for the index, and underweights in Micron (+240%), "
    f"Palantir (+135%) and Broadcom (+51%). Meta, "
    f"at about {BOT.loc['Meta Platforms, Inc.','Avg_active_weight']*100:.0f} points overweight, detracted modestly. The fund's average "
    f"{BOT.loc['Cash (Fidelity Cash Central Fund)','Avg_active_weight']*100:.0f}% cash holding cost "
    f"{bp(BOT.loc['Cash (Fidelity Cash Central Fund)','Contribution'])} bp in a rising market.")

r.h1("4. Conclusion")
r.p(f"The pre-set rule calls Contrafund's results <b>{m['verdict']}</b>. Over fifteen years its outperformance is explained by "
    f"a stable large-cap growth and momentum profile; the six-factor alpha of {pct(a6)} a year is not distinguishable from zero "
    f"(t = {t6:.2f}). In 2025 the holdings-based attribution does credit the managers with genuine selection, "
    f"{bp(E['Selection'])} bp, the largest of the three effects, but one strong year, much of it from a single private "
    f"company, is not proof of persistent skill. An investor holding Contrafund is mostly buying a growth/momentum tilt plus a "
    f"modest, noisy selection effect, at a performance-adjusted fee that rose from 0.56% (fiscal 2024) to 0.74% (fiscal 2025) after strong results.")
r.h1("Limitations")
r.bullets([
    "Buy-and-hold quarters ignore trading within each quarter; the residual captures it only in total.",
    "Private holdings are valued at Fidelity's fair values, which are estimates and are updated infrequently.",
    "Yahoo sectors differ from GICS. A handful of acquired or delisted companies without price history are left out "
    "(up to 0.5% of the fund); remaining weights are rescaled.",
    "The fee is applied as a uniform annual drag; the actual performance adjustment accrues over the year.",
])
r.h1("References")
r.bullets(["Brinson, G. and Fachler, N. (1985). Measuring Non-US Equity Portfolio Performance. <i>Journal of Portfolio Management</i>, 11(3), 73–76.",
           "Cariño, D. (1999). Combining Attribution Effects Over Time. <i>Journal of Performance Measurement</i>, 3(4), 5–14.",
           "Carhart, M. (1997). On Persistence in Mutual Fund Performance. <i>Journal of Finance</i>, 52(1), 57–82.",
           "Fama, E. and French, K. (2015). A Five-Factor Asset Pricing Model. <i>Journal of Financial Economics</i>, 116(1), 1–22."])
print("pages:", r.build())
