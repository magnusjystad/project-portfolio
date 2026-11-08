"""Builds report/rheinmetall_ic_memo.pdf (5 pages) from data/out_results.json and the notebook's CSV outputs."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import pandas as pd

from common.report import Report
from src import model as M

D, F = ROOT / "data", ROOT / "report" / "figures"
O = json.load(open(D / "out_results.json"))
mk, T = O["mk"], O["tests"]
WS = pd.read_csv(D / "out_wacc_sensitivity.csv", index_col=0)
PS = pd.read_csv(D / "out_peer_margins.csv", index_col=0)
BUD = pd.read_csv(D / "out_budget_eur.csv", index_col=0).iloc[:, 0]
H = M.history()
pct = lambda x, d=1: f"{x * 100:.{d}f}%"
eur = lambda x: f"€{x:,.0f}"
P = mk["price"]
CV = O["case_value"]
bud25, bud35 = BUD.loc[2025] / 1000, BUD.loc[2035] / 1000
peer_best = PS.drop("Rheinmetall")["Best year 2021–25"].max()
peer_avg_best = PS.drop("Rheinmetall")["5-yr average 2021–25"].max()

r = Report(ROOT / "report" / "rheinmetall_ic_memo.pdf", "Investment Committee Memo: Is Rheinmetall Priced for Perfection?",
           f"Investment Research Portfolio · Project 2 · Rheinmetall AG (RHM GY) · 7 October 2026 · price {eur(P)} (Xetra close)")
r.h1("Recommendation")
r.abstract(
    f"<b>Buy (long), 2% of NAV.</b> No: at {eur(P)} Rheinmetall is not priced for perfection. It is priced for very little. "
    f"With the brief's cost of capital (WACC {pct(mk['wacc'])}), the share price is justified by sales growth of only "
    f"{pct(O['a_cagr'])} a year from 2025 to 2035 at management's 20% margin. That means 2035 sales of €{O['a_sales_2035'] / 1000:,.1f}bn, "
    f"barely above the €13.7–14.2bn guided for 2026 alone. Alternatively, on management's sales path it implies a margin of "
    f"{pct(O['b_margin'])}. On all three tests (budget share, backlog and margin) the implied assumptions sit below our "
    f"base case, and even below our bear case, so the rule gives a Buy. The result depends heavily on the discount rate. "
    f"Our base case only equals today's price at a {pct(O['implied_wacc']['Base'])} discount rate, and the bear case at "
    f"{pct(O['implied_wacc']['Bear'])}. The market is either demanding a very high return or doubting that the order book "
    f"turns into durable earnings.")

r.h1("Thesis in three points")
r.bullets([
    f"<b>The price discounts almost no growth beyond 2026.</b> The shares have fallen from €1,797 (30 June 2025) to €990.50 "
    f"(30 June 2026) and {eur(P)} today. At our {pct(mk['wacc'])} WACC the market value equals a business that grows sales "
    f"{pct(O['a_cagr'])} a year to 2035. Even at a 9% WACC the implied 2035 sales (€{WS.iloc[3]['implied 2035 sales (EUR m)'] / 1000:,.1f}bn) "
    f"are below our bear case.",
    f"<b>The orders already exist.</b> The Rheinmetall Backlog was €{H.loc['Rheinmetall Backlog', 2025] / 1000:,.1f}bn at "
    f"end-2025 and €80.5bn at 30 June 2026, eight times 2025 sales. Book-to-bill was "
    f"{H.loc['Rheinmetall Nomination', 2025] / H.loc['Sales', 2025]:.1f}x in 2025. The price implies cumulative 2026–2030 sales "
    f"of €{T['backlog']['implied'] / 1000:,.0f}bn, less than the backlog on hand at mid-2026.",
    f"<b>Budgets give room even after a large share loss.</b> On the Hague path (3.5% of GDP core defence by 2035), European "
    f"NATO members' equipment spending rises from €{bud25:,.0f}bn (2025e) to €{bud35:,.0f}bn (2035). The price implies Rheinmetall's "
    f"European sales fall to {pct(T['budget']['implied'])} of that spending by 2035, from {pct(T['budget']['today'])} today. "
    f"Our base case needs {pct(T['budget']['Base'])}.",
])

kf = pd.DataFrame({y: [H.loc["Sales", y], H.loc["Operating result", y] / H.loc["Sales", y], H.loc["Rheinmetall Nomination", y],
                        H.loc["Rheinmetall Backlog", y], H.loc["Operating free cash flow (continuing)", y]] for y in [2022, 2023, 2024, 2025]},
                  index=["Sales (€m)", "Operating margin", "Rheinmetall Nomination (€m)", "Rheinmetall Backlog (€m)", "Operating FCF (€m)"])
kf["H1 2026"] = [5227, 786 / 5227, 16238, 80467, -1616]
kff = kf.astype(object)
for i in kf.index:
    kff.loc[i] = [pct(v) if "margin" in i else f"{v:,.0f}" for v in kf.loc[i]]
kff.columns = [str(c) for c in kff.columns]
kff.index.name = "Continuing operations"
r.table(kff, "Table 0. Key figures (annual report 2025, H1 2026 report). Guidance 2026: sales €13.7–14.2bn, margin ~19%; "
             "2030 target: ~€50bn, margin >20%, cash conversion >50%.")
r.image(F / "fig_backlog.png", 14, "Figure 0. Sales, order inflow (Rheinmetall Nomination) and backlog.")

r.h1("What the price implies")
r.p(f"<b>Method.</b> FCFF = operating result × (1 − {pct(mk['tax'])} tax) − reinvestment. Reinvestment is Δsales / {O['k']:.2f}, "
    "a sales-to-capital ratio calibrated so that management's own plan delivers its 50% cash-conversion target. The 2025 base "
    f"is €{M.SALES_2025:,.0f}m of continuing-operations sales at an {pct(M.MARGIN_2025)} operating margin. The margin moves "
    "linearly to its 2030 level and stays there; terminal growth is 2.0%.")
r.p(f"<b>Cost of capital.</b> CAPM cost of equity {pct(mk['ke'], 2)} = Bund {pct(mk['rf'], 2)} + Blume beta "
    f"{mk['beta_blume']:.2f} × Damodaran ERP {pct(mk['erp'], 2)}. Cost of debt {pct(mk['kd'], 2)} is the yield on Rheinmetall's "
    f"3.375% May 2031 bond at {mk['bond_price']:.2f} (Börse Frankfurt; Excel YIELD gives the same). Weights are "
    f"{pct(mk['w_e'], 0)} equity (€{mk['mcap'] / 1000:,.1f}bn) and {pct(1 - mk['w_e'], 0)} debt and pensions. WACC = "
    f"<b>{pct(mk['wacc'], 2)}</b>. <i>Caveat:</i> the five-year raw beta against the STOXX Europe 600 is {mk['beta_raw']:.2f} with "
    f"R² {mk['beta_r2']:.2f} and standard error {mk['beta_se']:.2f}. Rheinmetall's returns have had almost nothing to do with "
    "the European market since 2021, so this beta is statistically meaningless and the WACC is a floor rather than an "
    "estimate. Table 2 shows how far the result depends on it.")
r.image(F / "fig_grid.png", 16.5, "Figure 1. Value per share by 2025–2035 sales CAGR and margin; the black line is today's price. "
                                  "Bold cells are within 10% of the price.")
r.p(f"<b>Goal Seek results</b> (workbook model/rheinmetall_reverse_dcf.xlsx). (a) At management's 20% margin, the price implies a "
    f"<b>{pct(O['a_cagr'])}</b> sales CAGR for 2025–2035. (b) At management's sales path (2026 guidance midpoint €13.95bn, "
    f"€50bn in 2030, then growing with European equipment budgets), it implies a steady-state operating margin of "
    f"<b>{pct(O['b_margin'])}</b>.")
tests = pd.DataFrame({
    "Implied by price": [pct(T["budget"]["implied"]), f"€{T['backlog']['implied'] / 1000:,.0f}bn", pct(T["margin"]["implied"])],
    "Bear": [pct(T["budget"]["Bear"]), f"€{T['backlog']['Bear'] / 1000:,.0f}bn", pct(T["margin"]["Bear"])],
    "Base": [pct(T["budget"]["Base"]), f"€{T['backlog']['Base'] / 1000:,.0f}bn", pct(T["margin"]["Base"])],
    "Bull": [pct(T["budget"]["Bull"]), f"€{T['backlog']['Bull'] / 1000:,.0f}bn", pct(T["margin"]["Bull"])],
    "Reference": [f"today {pct(T['budget']['today'])}", "backlog €80.5bn (Jun 2026)",
                  f"peers' best year {pct(peer_best)}; best 5-yr avg {pct(peer_avg_best)}"]},
    index=["Budget: share of European NATO equipment spending, 2035", "Backlog: cumulative sales 2026–2030",
           "Margin: operating margin from 2030"])
tests.index.name = "Test"
r.table(tests, "Table 1. The three tests. The rule: Sell if the implied assumptions exceed our bull case on two of three, "
               "Hold if they sit between base and bull, Buy if they are below base. All three are below base, so: <b>Buy</b>.",
        col_widths=[5.2 * 28.35, 2.2 * 28.35, 1.8 * 28.35, 1.8 * 28.35, 1.8 * 28.35, 4.4 * 28.35], font=7.5)
ws = WS.copy()
ws.index = [pct(float(i)) for i in ws.index]
wsf = pd.DataFrame({"Implied CAGR (20% margin)": ws["implied CAGR 2025-35 (20% margin)"].map(pct),
                    "Implied 2035 sales": ws["implied 2035 sales (EUR m)"].map(lambda v: f"€{v / 1000:,.1f}bn"),
                    "Implied margin (mgmt sales)": ws["implied margin (mgmt sales path)"].map(pct),
                    "Bear value": ws["Bear value/share"].map(eur), "Base value": ws["Base value/share"].map(eur),
                    "Bull value": ws["Bull value/share"].map(eur)})
wsf.index.name = "WACC"
r.table(wsf, f"Table 2. Dependence on the discount rate (first row = model WACC). The price equals the bear case at "
             f"{pct(O['implied_wacc']['Bear'])}, the base case at {pct(O['implied_wacc']['Base'])} and the bull case at "
             f"{pct(O['implied_wacc']['Bull'])}.", font=7.5)

r.h1("Our view vs. the market")
r.p("Our three cases start from the 2026 guidance midpoint (€13.95bn), reach a 2030 sales level, and then grow with "
    "European equipment budgets to 2035:")
r.bullets([
    f"<b>Bear</b>: €30bn sales in 2030 (40% below management's target), 15% margin, close to Kongsberg's best year "
    f"({pct(PS.loc['Kongsberg Gruppen', 'Best year 2021–25'])}). Value {eur(CV['Bear'])}.",
    f"<b>Base</b>: €40bn in 2030, which is close to consensus for 2028 (€24.5bn on MarketScreener; our base has €23.6bn). The "
    f"margin is held at the 2025 level of 18.5%. Value {eur(CV['Base'])}.",
    f"<b>Bull</b>: management's plan, €50bn in 2030 at 21% (target: above 20%). Value {eur(CV['Bull'])}.",
])
r.image(F / "fig_budget.png", 16, "Figure 2. Budget test. Even the bull case needs about 15% of European equipment spending "
                                    "by 2030 (2025: 4.6%), a large but not impossible share for the continent's main land-systems "
                                    "and ammunition supplier. The price implies a falling share.")
r.p(f"The market's scepticism is not irrational. Rheinmetall's operating margin is already above every peer's best year "
    f"(Kongsberg {pct(PS.loc['Kongsberg Gruppen', 'Best year 2021–25'])}, Thales {pct(PS.loc['Thales', 'Best year 2021–25'])}, "
    f"BAE {pct(PS.loc['BAE Systems', 'Best year 2021–25'])}). Free cash flow was −€1.6bn in H1 2026 as working capital "
    "built up. The German Ministry of Defence also cancelled the F126 frigate programme in June 2026, in which Blohm + Voss "
    "was a subcontractor. But a share price that needs neither growth nor today's margin to be justified leaves a wide margin "
    "of safety.")
r.image(F / "fig_margins.png", 16, "Figure 3. Margin test: EBIT margin of the five peers (MarketScreener) vs. the margin implied "
                                   "at management's sales path.")

r.h1("Catalysts")
r.bullets([
    "<b>5 November 2026: Q3 statement.</b> Delivery of the €13.7–14.2bn 2026 guidance requires a strong H2 (H1: €5.2bn). "
    "Order intake is the key read-across to 2027.",
    "<b>Q4 2026: closing of the sale of the civilian business to AEQUITA</b> (signed June 2026). This simplifies the equity "
    "story and adds proceeds; our bridge only counts book value.",
    "<b>National budgets for 2027</b> and NATO's 2027 capability targets: confirmation that the 3.5% path is being funded.",
    "<b>Cash conversion:</b> a return to positive operating free cash flow would answer the main bear point (H1 2026 cash "
    "conversion was −205%).",
])

r.h1("Risks and what would prove us wrong (pre-mortem)")
r.p("Three specific ways this long loses money:")
r.bullets([
    "<b>Peace and budget fatigue.</b> A durable settlement in Ukraine could lead governments to stretch the 3.5% path, and "
    "national budget pressures could push back orders. Our bear case already assumes sales 40% below plan. A path that "
    "stays near 2% of GDP would put even that at risk.",
    "<b>Execution and cash.</b> Capacity ramp-ups (ammunition plants, the NVL shipyards) slip, and working capital keeps "
    "absorbing cash. The ROCE-based reinvestment assumption would then be too light. A sales-to-capital ratio half as high "
    "as calibrated would cut value materially.",
    "<b>Margin normalisation.</b> Governments push back on pricing as competition from new capacity (and from U.S. and "
    "Korean suppliers) increases. Margins fall towards the 10–12% that BAE and Thales have averaged. Our bear case assumes 15%.",
])
r.p("<b>What would make us change our minds:</b> order intake below sales for two consecutive quarters (book-to-bill under "
    "1), a cut to the 2026 guidance, or German budget plans that fall short of the 3.5% path.")

r.h1("Position sizing")
r.bullets([
    "2% of NAV at entry (around €926).",
    "Stop-loss at −25% from entry (about €695), the mirror of the brief's +25% stop for a short.",
    "Review at every quarterly report (next: 5 November 2026) against the three tests: the backlog conversion, the "
    "implied budget share and the margin.",
])
r.p("<i>Sources: Rheinmetall annual reports 2019–2025 and H1 2026 report; Capital Markets Day 2025 and September 2026 investor "
    "presentation (2030 targets); NATO, Defence Expenditure of NATO Countries (2014–2026), July 2026, read by OCR and checked against "
    "NATO's own totals; IMF World Economic Outlook GDP; Bundesbank; Damodaran; Börse Frankfurt; MarketScreener; yfinance. "
    "Model: model/rheinmetall_reverse_dcf.xlsx (checked against src/model.py by src/check_workbook.py). Written as a learning "
    "exercise; not investment advice.</i>")
print("pages:", r.build())
