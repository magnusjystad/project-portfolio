"""Builds report/rational_initiation.pdf (12 pages) from the notebook outputs in data/out_*.csv / out_valuation.json."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import pandas as pd

from common.report import Report
from src import model as M

D, F = ROOT / "data", ROOT / "report" / "figures"
V = json.load(open(D / "out_valuation.json"))
HS = pd.read_csv(D / "out_history_summary.csv", index_col=0)
FB = pd.read_csv(D / "out_forecast_base.csv", index_col=0)
FBe = pd.read_csv(D / "out_forecast_bear.csv", index_col=0)
FBu = pd.read_csv(D / "out_forecast_bull.csv", index_col=0)
SC = pd.read_csv(D / "out_scenarios.csv", index_col=0)
SE = pd.read_csv(D / "out_sensitivity.csv", index_col=0)
CT = pd.read_csv(D / "out_comps.csv", index_col=0)
RO = pd.read_csv(D / "out_roic.csv", index_col=0)
VC = pd.read_csv(D / "out_vs_consensus.csv", index_col=0)
RH = M.regions_history()
H1 = M.h1_2026()
pct = lambda x, d=1: f"{x * 100:.{d}f}%"
eur = lambda x, d=0: f"€{x:,.{d}f}"
P, TP, UP = V["price"], V["target"], V["upside"]
MCAP = P * M.SHARES
EV_MKT = MCAP - V["net_cash"]
beta_implied = (V["implied_ke"] - V["rf"]) / V["erp"]
n_sell = int((SE / P - 1 <= -0.10).values.sum())

r = Report(ROOT / "report" / "rational_initiation.pdf", "Rational AG (RAA GY) — Initiation of Coverage",
           f"Investment Research Portfolio · Project 1 · Capital goods / commercial kitchen equipment · 7 October 2026 · "
           f"Price {eur(P, 2)} (Xetra close, 7 Oct 2026)")
r.h1(f"Rating: {V['rating'].upper()} · 12-month price target {eur(TP)} ({pct(UP, 0)})")
r.abstract(
    "<b>A superb business at a price that needs a low discount rate.</b> Rational dominates combi-steaming with around half "
    "of the world market, earns a return on invested capital of 65% and has no debt. None of that is in question. What is "
    f"in question is the price. At {eur(P, 2)} the shares trade on {CT.loc['Rational', 'P/E NTM']:.1f}× next-twelve-month "
    f"earnings and {CT.loc['Rational', 'EV/EBIT NTM']:.1f}× EV/EBIT, a {pct(V['premium']['P/E'], 0)} and "
    f"{pct(V['premium']['EV/EBIT'], 0)} premium to Middleby, Electrolux Professional and Hoshizaki. Our ten-year DCF, using "
    f"the cost of equity the brief prescribes ({pct(V['ke'], 2)}), gives a probability-weighted 12-month target of {eur(TP)}. "
    f"That is {pct(-UP, 0)} below the share price, so the rating rule gives Sell.")
r.bullets([
    f"<b>Growth has normalised.</b> Sales grew 6.0% in 2024, 5.5% in 2025 and 5.8% in H1 2026, down from a 2016–2019 "
    f"average of {pct(HS.loc[2017:2019, 'Growth'].mean(), 0)}. China fell 29% in 2025, Asia is still shrinking (−2% in H1 2026) "
    f"and US tariffs cost about one point of gross margin. Our base case (+5.9% in 2026, 6–7% a year to 2030) sits slightly below "
    f"consensus: our 2026 EBIT is {pct(VC.loc[2026, 'EBIT vs consensus'], 1)} below.",
    f"<b>The discount rate has changed, not the business.</b> The 10-year Bund yields {pct(V['rf'], 2)} against roughly zero "
    f"in 2016–2021. Rational's five-year beta against the STOXX Europe 600 is {V['beta_raw']:.2f} ({V['beta_blume']:.2f} "
    f"Blume-adjusted). At today's price the market is discounting at {pct(V['implied_ke'], 1)}, which is a beta of about "
    f"{beta_implied:.2f}.",
    f"<b>The call holds across the sensitivity grid.</b> {n_sell} of the 25 combinations of cost of equity (±1pp) and "
    f"terminal growth (1–3%) give a Sell. Even the bull case ({eur(V['dcf']['Bull']['target'])}: 28% EBIT margins and 6.7% "
    "a year of sales growth for a decade) is below the share price.",
])
kf = pd.DataFrame({
    "2023A": [HS.loc[2023, "Sales"], HS.loc[2023, "Growth"], HS.loc[2023, "EBIT"], HS.loc[2023, "EBIT margin"], HS.loc[2023, "EPS (EUR)"], None],
    "2024A": [HS.loc[2024, "Sales"], HS.loc[2024, "Growth"], HS.loc[2024, "EBIT"], HS.loc[2024, "EBIT margin"], HS.loc[2024, "EPS (EUR)"], None],
    "2025A": [HS.loc[2025, "Sales"], HS.loc[2025, "Growth"], HS.loc[2025, "EBIT"], HS.loc[2025, "EBIT margin"], HS.loc[2025, "EPS (EUR)"], None],
    "2026E": [FB.loc[2026, "Sales"], FB.loc[2026, "Growth"], FB.loc[2026, "EBIT"], FB.loc[2026, "EBIT margin"], None, FB.loc[2026, "FCFF"]],
    "2027E": [FB.loc[2027, "Sales"], FB.loc[2027, "Growth"], FB.loc[2027, "EBIT"], FB.loc[2027, "EBIT margin"], None, FB.loc[2027, "FCFF"]],
    "2028E": [FB.loc[2028, "Sales"], FB.loc[2028, "Growth"], FB.loc[2028, "EBIT"], FB.loc[2028, "EBIT margin"], None, FB.loc[2028, "FCFF"]],
}, index=["Sales (EUR m)", "Growth", "EBIT (EUR m)", "EBIT margin", "EPS (EUR, reported)", "FCFF (EUR m)"])
fmt = {"Sales (EUR m)": lambda x: f"{x:,.0f}", "Growth": lambda x: pct(x), "EBIT (EUR m)": lambda x: f"{x:,.0f}",
       "EBIT margin": lambda x: pct(x), "EPS (EUR, reported)": lambda x: f"{x:.2f}", "FCFF (EUR m)": lambda x: f"{x:,.0f}"}
kf = kf.apply(lambda row: row.map(lambda v: "–" if pd.isna(v) else fmt[row.name](v)), axis=1)
kf.index.name = "Key financials"
r.table(kf, "Key financials. A = reported (annual reports); E = this report's base case. FCFF = free cash flow to firm after "
            "lease payments. EPS forecasts are not shown because the model values the business on EBIT and holds net cash separately.")
kd = pd.DataFrame({"Market data": ["Market capitalisation", "Net cash (30 Jun 2026)", "Enterprise value", "52-week range",
                                   "Free float", "Shares outstanding"],
                   "Value": [f"€{MCAP:,.0f}m", f"€{V['net_cash']:,.0f}m", f"€{EV_MKT:,.0f}m", f"{eur(V['lo52'], 1)} – {eur(V['hi52'], 0)}",
                             "44.8% (55.2% held by the founding family's holding)", "11.37m"]})
r.table(kd, None, index=False, col_widths=[6 * 28.35, 9 * 28.35])

r.pagebreak()
r.h1("1. Investment thesis")
r.p("Our case is about the price of quality, not its existence. We rate the shares Sell for three reasons.")
r.h2("1.1 Quality is fully recognised")
r.p(f"Rational is a textbook compounder. Sales grew from €613m in 2016 to €1,260m in 2025 ({pct((1259.558 / 613.010) ** (1 / 9) - 1)} a "
    f"year). The EBIT margin was above 26% in every year outside the pandemic, and ROIC averaged {pct(RO['roic'].mean(), 0)} over "
    f"2016–2025 against a cost of capital of {pct(RO['ke'].min(), 0)}–{pct(RO['ke'].max(), 0)} (Figure 4). That gap explains why "
    "Rational trades at a premium to its peers. The question for an investor is whether today's premium is still too large, "
    f"and at {CT.loc['Rational', 'P/E NTM']:.0f}× earnings it is: the peers' median NTM P/E is {V['peer_median']['P/E']:.0f}×.")
r.h2("1.2 Growth is now mid-single-digit")
r.p(f"From 2016 to 2019 sales grew by about {pct(HS.loc[2017:2019, 'Growth'].mean(), 0)} a year. They rebounded strongly after "
    "the pandemic (+20% in 2021, +31% in 2022) and have since settled at 5.5–6%. H1 2026 sales rose 5.8% (€641.5m), with Europe "
    "ex-Germany +9%, North America +4%, Asia −2% and the rest of the world −10%. Management's own long-term ambition is "
    "\"mid to high single-digit\" growth. Our base case assumes 5.9% in 2026, 6.5–6.6% a year from 2027 to 2030, then a fade to 3% "
    "by 2035, which puts it slightly below consensus for 2026–2027.")
r.h2("1.3 The cost of capital is no longer near zero")
r.p(f"Between 2016 and 2021 the 10-year Bund yield was −0.6% to +0.5%. Today it is {pct(V['rf'], 2)}. With Damodaran's implied "
    f"equity risk premium of {pct(V['erp'], 2)} and a Blume-adjusted beta of {V['beta_blume']:.2f}, the brief's CAPM gives "
    f"{pct(V['ke'], 2)}. Rational has net cash, so this is also its WACC. The current price implies a discount rate of "
    f"{pct(V['implied_ke'], 1)}. The bull case for the shares therefore rests on investors continuing to treat Rational as "
    f"low-risk (a beta near {beta_implied:.1f}, close to the 0.74 one-year MDAX beta the company reports). Its own share price "
    f"over the last five years argues otherwise: monthly returns moved {V['beta_raw']:.1f}× as much as the European market "
    f"(R² {V['beta_r2']:.2f}).")
r.image(F / "fig_share_price.png", 16, "Figure 1. Rational (total return) vs. STOXX Europe 600, October 2021 – October 2026.")

r.h1("2. Business")
r.p("Rational, founded in 1973 in Landsberg am Lech (Bavaria), makes two cooking systems for professional kitchens:")
r.bullets([
    "<b>iCombi</b> (88% of 2025 sales): combi-steamers that cook with steam, hot air or both, under software that controls the cooking "
    "process. They replace grills, stoves and ovens. The iCombi Pro is the flagship; the iCombi Classic is a manual model; the "
    "iCombi One, made in China, is sold only there.",
    f"<b>iVario</b> ({pct(HS.loc[2025, 'iVario share'], 0)} of 2025 sales, up from {pct(HS.loc[2016, 'iVario share'], 0)} in 2016): "
    "multifunction pans that cook with contact heat or in liquid. They replace fryers, boiling pans and tilting pans. "
    "iVario sales grew 14% in H1 2026, against 5% for iCombi.",
    "<b>After-sales</b>: accessories, spare parts, care products and service were 31% of sales in both 2025 and H1 2026. This "
    "recurring revenue base supports margins.",
])
r.p("Customers range from restaurants, hotels and caterers to hospitals, schools, military kitchens, quick-service chains, "
    "supermarkets and ghost kitchens. Rational sells mainly through dealers, supported by its own sales and chef-training "
    "staff. Production is in Landsberg (combi-steamers) and Wittenheim, France (iVario), plus a plant in China for the "
    "iCombi One. The company had 2,912 employees at 30 June 2026. The founding family's holding company owns 55.2% of the "
    "shares; the rest is free float (AR 2025).")
reg = pd.DataFrame({y: RH.loc[y] for y in [2016, 2019, 2022, 2025]})
reg.loc["Total"] = reg.sum()
reg["CAGR 2016–25"] = (reg[2025] / reg[2016]) ** (1 / 9) - 1
reg["Share 2025"] = reg[2025] / reg.loc["Total", 2025]
reg["H1 2026 growth"] = [H1["germany"] / 60.411 - 1, H1["europe_ex_germany"] / 262.489 - 1, H1["north_america"] / 147.783 - 1,
                         H1["asia"] / 66.773 - 1, (H1["latin_america"] + H1["rest_of_world"]) / (34.119 + 34.660) - 1,
                         H1["sales"] / H1["sales_h1_2025"] - 1]
regf = reg.copy()
for c in [2016, 2019, 2022, 2025]:
    regf[c] = reg[c].map(lambda x: f"{x:,.0f}")
for c in ["CAGR 2016–25", "Share 2025", "H1 2026 growth"]:
    regf[c] = reg[c].map(lambda x: pct(x))
regf.index.name = "Sales by customer region (EUR m)"
r.table(regf, "Table 1. Sales by customer region. Rest of world includes Latin America (reported separately by Rational: €84.6m "
              "in 2025). Sources: annual reports' regional breakdown; H1 2026 report.")

r.h1("3. Industry and competition")
r.p("Rational estimates that about 4.8 million kitchens could use a combi-steamer and that only around 25% currently do, and "
    "that the iVario's addressable market is about 1.6 million customers (AR 2025). It puts its own share of the combi-steamer "
    "market at around 50%. Demand is driven by the number of meals eaten outside the home, labour shortages in kitchens (which "
    "favour automated cooking), and energy and space costs. It is also tied to the restaurant capex cycle: a combi-steamer is a "
    "discretionary purchase that customers delay when their margins are squeezed, as in 2020 (sales −23%).")
pe = CT.copy()
peer_tab = pd.DataFrame({
    "Listing": ["Xetra (EUR)", "Nasdaq (USD)", "Stockholm (SEK)", "Tokyo (JPY)"],
    "Focus": ["Combi-steamers, multifunction pans", "Commercial foodservice and residential kitchen equipment",
              "Food, beverage and laundry equipment", "Ice machines, refrigerators, dishwashers"],
    "EBIT margin 2026E": [pct(x) for x in pe["EBIT margin FY1"]],
    "EV/EBIT NTM": [f"{x:.1f}×" for x in pe["EV/EBIT NTM"]], "P/E NTM": [f"{x:.1f}×" for x in pe["P/E NTM"]]}, index=pe.index)
r.table(peer_tab, "Table 2. Listed peers. EBIT margin = consensus 2026 EBIT / consensus 2026 sales. Multiples: price on 7 Oct "
                  "2026 (Hoshizaki 6 Oct) and MarketScreener consensus; NTM = 23% FY2026 + 77% FY2027; EV uses consensus "
                  "end-2026 net debt.", col_widths=[3.4 * 28.35, 2.6 * 28.35, 5.2 * 28.35, 2.2 * 28.35, 1.9 * 28.35, 1.6 * 28.35], font=7.5)
r.p(f"Rational's margin is more than twice that of Electrolux Professional ({pct(pe.loc['Electrolux Professional', 'EBIT margin FY1'])}) "
    f"and Hoshizaki ({pct(pe.loc['Hoshizaki', 'EBIT margin FY1'])}) and well above Middleby's "
    f"({pct(pe.loc['Middleby', 'EBIT margin FY1'])}). None of the three is a pure combi-steamer company, so the comparison is "
    "imperfect; the multiples comparison should be read with that in mind. The competitive risk the annual report itself flags "
    "is that a larger competitor, created by mergers, could close the technology gap.")

r.h1("4. Financials")
r.image(F / "fig_revenue_build.png", 16.5, "Figure 2. Sales by region 2016–2025 (reported) and 2026–2035 (base case), with the "
                                          "iVario share of sales.")
r.p("The revenue build forecasts each customer region from its 2025 level, using growth rates set for each region "
    "(Appendix A). Within each region the iVario share is assumed equal to the group average, because Rational does not "
    "disclose the product × region split. The group iVario share rises by 0.5pp a year to 2030, in line with the 2016–2025 "
    "pace (+0.52pp a year), and by 0.3pp a year after that.")
hist = pd.DataFrame({y: [HS.loc[y, "Sales"], HS.loc[y, "Gross margin"], HS.loc[y, "EBIT margin"], HS.loc[y, "Net profit"],
                         HS.loc[y, "CFO"], HS.loc[y, "Capex"], HS.loc[y, "DPS paid in year (EUR)"]] for y in range(2016, 2026)},
                    index=["Sales", "Gross margin", "EBIT margin", "Net profit", "Operating cash flow", "Capex", "Dividend paid (EUR/share)"])
histf = hist.copy().astype(object)
for i in hist.index:
    histf.loc[i] = [pct(v) if "margin" in i else (f"{v:.2f}" if "EUR" in i else f"{v:,.0f}") for v in hist.loc[i]]
histf.index.name = "EUR m"
r.table(histf, "Table 3. Ten-year history from the annual reports (EUR m unless stated). Dividends paid include special "
               "dividends (€2.50 in 2022–2023; €4.00 paid in 2026 for fiscal 2025).", font=7)
r.image(F / "fig_margins.png", 16, "Figure 3. Gross and EBIT margins, reported and forecast by scenario.")
r.p("The EBIT margin has recovered from 16.4% (2020) to 26.4% (2025). Guidance for 2026 is 25–26%, which includes a one-off US "
    "tariff refund of about €14m. Without it, the margin would be roughly one point lower, so our 25.5% base case is "
    "mid-range. We assume 26.0% in 2027 and 26.5% from 2028, the pre-pandemic level. The balance sheet is very strong: equity "
    "is 77% of total assets and net financial assets were about €430m at 30 June 2026, after the €227.4m dividend.")

r.h2("4.1 First half of 2026")
h1t = pd.DataFrame({
    "H1 2026": [H1["sales"], H1["germany"], H1["europe_ex_germany"], H1["north_america"], H1["asia"], H1["latin_america"] + H1["rest_of_world"],
                H1["icombi"], H1["ivario"], H1["ebit"], H1["ebit"] / H1["sales"]],
    "H1 2025": [H1["sales_h1_2025"], 60.411, 262.489, 147.783, 66.773, 34.119 + 34.660, 536.618, 69.617, H1["ebit_h1_2025"],
                H1["ebit_h1_2025"] / H1["sales_h1_2025"]]},
    index=["Sales", "  Germany", "  Europe ex-Germany", "  North America", "  Asia", "  Rest of world incl. Latin America",
           "  iCombi", "  iVario", "EBIT", "EBIT margin"])
h1t["Change"] = h1t["H1 2026"] / h1t["H1 2025"] - 1
h1f = h1t.copy().astype(object)
for i in h1t.index:
    if i == "EBIT margin":
        h1f.loc[i] = [pct(h1t.loc[i, "H1 2026"]), pct(h1t.loc[i, "H1 2025"]), f"{(h1t.loc[i, 'H1 2026'] - h1t.loc[i, 'H1 2025']) * 100:+.1f}pp"]
    else:
        h1f.loc[i] = [f"{h1t.loc[i, 'H1 2026']:,.1f}", f"{h1t.loc[i, 'H1 2025']:,.1f}", f"{h1t.loc[i, 'Change']:+.1%}"]
h1f.index = [i.replace("  ", "– ") for i in h1f.index]
h1f.index.name = "EUR m"
r.table(h1f, "Table 4. H1 2026 vs. H1 2025 (H1 2026 report). The EBIT margin includes the US tariff refund; the company "
             "states a currency-adjusted margin of 26.8%.", col_widths=[6.5 * 28.35, 2.5 * 28.35, 2.5 * 28.35, 2.5 * 28.35])
r.h2("4.2 Cash flow and capital allocation")
cf = pd.DataFrame({y: [HS.loc[y, "CFO"], -HS.loc[y, "Capex"], HS.loc[y, "FCF (CFO − capex)"], HS.loc[y, "DPS paid in year (EUR)"] * M.SHARES,
                       HS.loc[y, "Cash + deposits"]] for y in range(2016, 2026)},
                  index=["Operating cash flow", "Capex", "Free cash flow", "Dividends paid", "Cash and deposits (31 Dec)"])
cff = cf.map(lambda x: f"{x:,.0f}")
cff.index.name = "EUR m"
r.table(cff, "Table 5. Cash flow and liquidity (annual reports). Deposits = fixed-term deposits or other current financial assets.", font=7)
r.p(f"From 2016 to 2025 Rational generated €{cf.loc['Free cash flow'].sum():,.0f}m of free cash flow and paid out "
    f"€{cf.loc['Dividends paid'].sum():,.0f}m in dividends ({cf.loc['Dividends paid'].sum() / cf.loc['Free cash flow'].sum():.0%}). "
    "It has not bought back shares, and the share count has been 11.37m throughout. Capex peaked at 5.9% of sales in 2018 "
    "(capacity expansion in Landsberg and Wittenheim) and has since run at about 3%. The new service-parts building raised H1 "
    "2026 capex to €16.5m from €9.1m.")

r.h1("5. Valuation")
r.h2("5.1 Discounted cash flow")
r.p(f"We value free cash flow to the firm over 2026–2035 and add a terminal value growing at {pct(M.G_TERM)} a year. The "
    f"discount rate is the cost of equity from CAPM: risk-free rate {pct(V['rf'], 2)} (Bundesbank 10-year Bund yield on "
    f"{V['rf_date']}) + beta {V['beta_blume']:.3f} (Blume-adjusted from a raw {V['beta_raw']:.3f}, 60 monthly returns against the "
    f"STOXX Europe 600, October 2021 – September 2026, standard error {V['beta_se']:.2f}) × ERP {pct(V['erp'], 2)} (Damodaran "
    f"implied ERP, {V['erp_month'][:7]}) = {pct(V['ke'], 2)}. Rational has no financial debt, so WACC equals the cost of equity. "
    "Lease payments are deducted from FCFF. Net cash at 30 June 2026 (cash, fixed-term deposits and fund units, less "
    f"pensions: €{V['net_cash']:,.0f}m) is added to enterprise value. The 12-month target is today's value per share "
    "grown at the cost of equity, less the FY2026 dividend payable in May 2027 (70% payout).")
sct = pd.DataFrame({
    "Bear (25%)": [pct(SC.loc["Sales CAGR 2025–35", "Bear"]), pct(SC.loc["EBIT margin 2028+", "Bear"]), f"{SC.loc['EV', 'Bear']:,.0f}",
                   eur(SC.loc["Value per share", "Bear"]), eur(SC.loc["12-month target", "Bear"]), pct(SC.loc["TV share of EV", "Bear"], 0)],
    "Base (50%)": [pct(SC.loc["Sales CAGR 2025–35", "Base"]), pct(SC.loc["EBIT margin 2028+", "Base"]), f"{SC.loc['EV', 'Base']:,.0f}",
                   eur(SC.loc["Value per share", "Base"]), eur(SC.loc["12-month target", "Base"]), pct(SC.loc["TV share of EV", "Base"], 0)],
    "Bull (25%)": [pct(SC.loc["Sales CAGR 2025–35", "Bull"]), pct(SC.loc["EBIT margin 2028+", "Bull"]), f"{SC.loc['EV', 'Bull']:,.0f}",
                   eur(SC.loc["Value per share", "Bull"]), eur(SC.loc["12-month target", "Bull"]), pct(SC.loc["TV share of EV", "Bull"], 0)]},
    index=["Sales CAGR 2025–2035", "EBIT margin 2028–2035", "Enterprise value (EUR m)", "Value per share today", "12-month target",
           "Terminal value / EV"])
sct.index.name = "Scenario"
r.table(sct, f"Table 6. Scenarios. Bear: regional growth 2pp lower in 2026 and 3pp lower in 2027–2030, EBIT margin 24%. "
             f"Bull: +1pp and +2pp, margin 28%. Probability-weighted target: <b>{eur(TP, 2)}</b>.")
br = pd.DataFrame({s_: [V["dcf"][s_]["pv_explicit"], V["dcf"][s_]["pv_tv"], V["dcf"][s_]["ev"], V["net_cash"], V["dcf"][s_]["equity"],
                       V["dcf"][s_]["value_per_share"], V["dcf"][s_]["value_per_share"] * V["ke"], -V["dcf"][s_]["dps_next12m"],
                       V["dcf"][s_]["target"]] for s_ in ["Bear", "Base", "Bull"]},
                  index=["PV of FCFF, H2 2026–2035", "PV of terminal value", "Enterprise value", "+ Net cash (30 Jun 2026)",
                         "Equity value", "Value per share (EUR)", "+ 12 months at the cost of equity (EUR)",
                         "− FY2026 dividend paid May 2027 (EUR)", "12-month target (EUR)"])
brf = br.copy().astype(object)
for i in br.index:
    brf.loc[i] = [f"{v:,.2f}" if "EUR)" in i else f"{v:,.0f}" for v in br.loc[i]]
brf.index.name = "EUR m"
r.table(brf, "Table 7. From enterprise value to the 12-month target, by scenario.")
sen = SE.copy()
sen.index = [f"ke {i}" for i in sen.index]
sen = sen.map(lambda x: f"€{x:,.0f} ({x / P - 1:+.0%})")
sen.index.name = "Cost of equity \\ g"
r.table(sen, f"Table 8. Probability-weighted 12-month target (upside vs. {eur(P, 2)}) by cost of equity and terminal growth. "
             f"{n_sell} of 25 cells imply Sell (≤ −10%).", font=7.5)
r.h2("5.2 What the share price implies")
rv = V["reverse_dcf"]
r.p(f"Holding the base case fixed, the share price of {eur(P, 2)} is consistent with a cost of equity of {pct(V['implied_ke'], 1)} "
    f"(a beta of about {beta_implied:.2f}). Keeping our {pct(V['ke'], 2)} cost of equity, the price instead needs either "
    f"(a) sales growth about {rv['growth_shift_2027_2030'] * 100:.0f} points a year higher in every region from 2027 to 2030 "
    f"(roughly 15% a year, more than twice the rate of the last three years), or (b) an EBIT margin of "
    f"{pct(rv['ebit_margin_2027_on'], 0)} from 2027, against a ten-year high of 27.2% (2016). Neither looks likely. The real "
    "debate is about the discount rate.")
r.h2("5.3 Comparables and the ROIC premium")
r.p(f"At the peer-median NTM EV/EBIT ({V['peer_median']['EV/EBIT']:.1f}×) Rational would be worth "
    f"{eur(V['implied_by_multiples']['EV/EBIT at peer median'])} a share; at the peer-median P/E ({V['peer_median']['P/E']:.1f}×), "
    f"{eur(V['implied_by_multiples']['P/E at peer median'])}. A premium is deserved. Figure 4 shows ROIC between 32% (2020) and "
    "105% (2016) against a cost of capital of 7–10%, a spread none of the peers matches. But the market already pays "
    f"{pct(V['premium']['EV/EBIT'], 0)} more per euro of EBIT. Our DCF, which credits Rational with its higher growth and "
    "margins, still lands below the share price.")
r.image(F / "fig_roic_vs_wacc.png", 16, "Figure 4. ROIC (NOPAT / average invested capital; invested capital = equity + "
                                          "pensions − cash and deposits) vs. cost of capital (year-end Bund + 1.49 × Damodaran ERP).")
r.image(F / "fig_valuation_range.png", 16, "Figure 5. Valuation summary.")

r.h1("6. Catalysts")
r.bullets([
    "<b>5 November 2026 — 9M 2026 statement.</b> Q3 2025 sales were €312.0m; the 9M print shows whether full-year growth "
    "reaches the 'mid to high single-digit' guidance. To hit 7% for 2026, H2 sales must rise about 8%. Our base case assumes 6%.",
    "<b>19 November 2026 — Capital Markets Day</b> (AR 2025 financial calendar). Any mid-term targets for China, North America "
    "and the iVario could move expectations either way.",
    "<b>March 2027 — FY2026 results and 2027 guidance.</b> 2027 is the first full year without the tariff refund. The dividend "
    "proposal (policy ~70% payout, plus specials in some years) is announced with the results.",
    "<b>US tariff decisions.</b> Rational makes everything in Europe and exports to the US; North America was 24% of H1 2026 sales.",
])
r.h1("7. Risks to our rating")
r.p("Upside risks (to a Sell):")
r.bullets([
    "<b>Lower discount rate.</b> At the beta the share price implies (about 0.88) our target would be close to today's price. "
    "If Bund yields fall back, or the market keeps treating Rational as defensive, the shares can stay expensive.",
    "<b>Faster growth.</b> China re-accelerating with the iCombi One, iVario penetration, or a strong replacement cycle. Our bull "
    "case (6.7% a year for ten years, 28% margins) is worth €485.",
    "<b>Capital return.</b> Net cash of about €430m (6.6% of market capitalisation) could fund special dividends or buybacks.",
])
r.p("Downside risks (that would make the stock cheaper still):")
r.bullets([
    "<b>US tariffs:</b> management estimates about one point of gross margin; higher rates or a loss of the price increases (4–5% "
    "in the US) would hit margins further.",
    "<b>China:</b> sales fell 29% in 2025; Asia declined again in H1 2026 (−2%).",
    "<b>Restaurant capex cycle:</b> 2020 showed sales can fall more than 20% when customers stop investing.",
    "<b>Competition:</b> the annual report names the risk of larger competitors formed by mergers catching up technologically.",
])

r.pagebreak()
r.h1("Appendix A. Forecast assumptions")
ga = pd.DataFrame({reg_: [pct(M.BASE_GROWTH[reg_][0]), pct(M.BASE_GROWTH[reg_][1]), pct(M.FADE_TO),
                          pct((RH.loc[2025, reg_] / RH.loc[2016, reg_]) ** (1 / 9) - 1)] for reg_ in M.REGIONS},
                  index=["2026", "2027–2030", "2035 (linear fade from 2031)", "Reported CAGR 2016–2025"]).T
ga.index.name = "Base-case sales growth"
r.table(ga, "Table A1. Base-case regional growth (EUR, nominal). Bear: −2pp (2026) and −3pp (2027–2030); bull: +1pp and +2pp. "
            "All scenarios fade to 3% by 2035.")
ca = pd.DataFrame({"Assumption": ["Tax rate on EBIT", "D&A / sales", "Capex / sales", "Net working capital / sales",
                                  "Lease payments / sales", "Dividend payout", "iVario share step (base)", "EBIT margin (bear / base / bull)"],
                   "Value": ["25.0%", "3.0%", "3.5% (2026–27), 3.2% after", "22.5%", "0.9%", "70%", "+0.5pp a year to 2030, +0.3pp after",
                             "24.0% / 26.5% / 28.0% from 2028"],
                   "Evidence": ["Effective rate 23.1% (2024), 25.6% (2025)", "2.9–3.1% in 2022–2025",
                                "New service-parts building; 2.6–3.1% in 2023–2025", "21.4–24.9% in 2021–2025",
                                "0.94% in 2025", "Company policy (H1 2026 report)", "+0.52pp a year 2016–2025",
                                "26.4–27.2% in 2016–2019 and 2024–2025"]})
r.table(ca, "Table A2. Other forecast assumptions (identical across scenarios unless stated).", index=False,
        col_widths=[4.5 * 28.35, 5 * 28.35, 7.5 * 28.35], font=7.5)
fy = FB[["Sales", "Growth", "iVario share", "EBIT", "EBIT margin", "NOPAT", "D&A", "Capex", "Change in NWC", "Lease payments", "FCFF"]].T
fyf = fy.astype(object)
for i in fy.index:
    fyf.loc[i] = [pct(v) if i in ("Growth", "iVario share", "EBIT margin") else f"{v:,.0f}" for v in fy.loc[i]]
fyf.columns = [str(c) for c in fyf.columns]
fyf.index.name = "Base case, EUR m"
r.table(fyf, "Table A3. Base-case forecast, 2026–2035.", font=6.5)
r.h1("Appendix B. Reported statements, 2016–2025 (EUR m)")
Hh = M.history()
def stmt(rows, title):
    t = Hh.loc[[x for x in rows if x in Hh.index]].copy()
    t = t.map(lambda v: "–" if pd.isna(v) else f"{v:,.1f}")
    t.columns = [str(c) for c in t.columns]
    t.index.name = title
    r.table(t, None, font=6.5)
stmt(["Sales revenues", "Cost of sales", "Gross profit", "Sales and service expenses", "R&D expenses", "G&A expenses",
      "Other operating income", "Other operating expenses", "EBIT", "Interest income", "Interest expenses", "EBT", "Income taxes",
      "Net profit"], "Income statement")
stmt(["Intangible assets", "PP&E", "Inventories", "Trade receivables", "Fixed deposits > 3 months", "Other current financial assets",
      "Cash", "Total assets", "Equity", "Pensions", "Trade payables", "Total equity and liabilities"], "Balance sheet")
stmt(["CFO", "D&A", "Capex", "CFI", "Lease payments", "Dividends paid", "CFF", "Cash start", "Cash end"], "Cash flow statement")
r.caption("Extracted from the consolidated statements in each annual report (src/build_extracts.py). Blank cells: line not "
          "shown separately that year (e.g., deposits included in other current financial assets from 2018).")
r.h1("Appendix C. Comparables inputs")
ci = CT[["Currency", "Price (local)", "Market cap (local m)", "Net debt (local m)", "EBIT FY1", "EBIT FY2", "EPS FY1", "EPS FY2"]].copy()
for c in ci.columns[1:]:
    ci[c] = ci[c].map(lambda v: f"{float(v):,.2f}" if abs(float(v)) < 1000 else f"{float(v):,.0f}")
ci.index.name = "Company"
r.table(ci, "Table C1. Local-currency inputs: price (yfinance), shares (yfinance; Rational 11.37m), FY2026E net debt and "
            "FY2026–27E EBIT and EPS (MarketScreener consensus, 7 Oct 2026). Middleby's FY ends in early January.", font=7)
r.h1("Appendix D. Two-minute pitch")
for para in open(ROOT / "report" / "pitch_script.md").read().split("\n\n")[1:]:
    r.p(para.replace("**", ""))
r.h1("Appendix E. Data, method and model")
r.bullets([
    "Annual reports 2016–2025 and the H1 2026 report (rational-online.com). Statements, regional sales and product-group sales are "
    "extracted from the PDFs by src/build_extracts.py and reconciled. Regions sum to group sales in every year; gross profit, "
    "EBIT and the cash roll-forward reconcile.",
    "Prices: yfinance (RAA.DE, ^STOXX, MIDD, EPRO-B.ST, 6465.T). Risk-free: Deutsche Bundesbank daily 10-year Bund yield "
    f"({pct(V['rf'], 2)}; the ECB's euro-area AAA 10-year spot rate was 3.52% on 6 October). ERP: Damodaran ERPbymonth.xlsx. "
    "Consensus: MarketScreener pages saved on 7 October 2026.",
    "Model: model/rational_model.xlsx. Every forecast and valuation cell is an Excel formula. src/check_workbook.py "
    "recalculates it in LibreOffice and confirms it matches the Python model (src/model.py) to the cent.",
    "This report was written as a learning exercise. It is not investment advice, and the author holds no position.",
])
pages = r.build()
print("pages:", pages)
