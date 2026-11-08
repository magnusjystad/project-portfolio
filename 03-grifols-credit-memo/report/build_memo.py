"""Builds report/grifols_credit_memo.pdf from src/model.py, data/credit_history.csv and the notebook's figures."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import pandas as pd

from common.report import Report
from src import model as M

F = ROOT / "report" / "figures"
R = M.run()
H = pd.read_csv(ROOT / "data" / "credit_history.csv", index_col=0)
rv, Y = R["rv"], R["yields"]
cmw = lambda ws: [w * 28.35 for w in ws]
pct = lambda x, d=2: f"{x * 100:.{d}f}%"
bp = lambda x: f"{x * 1e4:,.0f}bp"
eur = lambda x: f"€{x:,.0f}m"
S, U = "7.125% secured 2030", "3.875% unsecured 2028"
ys, yu = Y["7.125% senior secured notes"], Y["3.875% senior unsecured notes"]
gap = R["gap"]
rb, rd = R["refi_base"], R["refi_down"]
e_down = R["down"].loc["Adjusted EBITDA", 2028]

r = Report(ROOT / "report" / "grifols_credit_memo.pdf", "Grifols: Secured 2030s or Unsecured 2028s?",
           "Investment Research Portfolio · Project 3 · High-yield credit memo · Grifols, S.A. (GRF SM) · 7 October 2026 "
           "(settlement 9 October 2026)")

# ---------------------------------------------------------------------------------------------------------------------
r.h1("Recommendation")
r.abstract(
    f"<b>Overweight the €1.4bn 3.875% senior unsecured notes due October 2028; Underweight the €1.3bn 7.125% senior secured "
    f"notes due May 2030.</b> Following the brief's rule, the unsecured notes offer the higher expected return by "
    f"{abs(gap) * 1e4:,.0f}bp ({pct(rv.loc['expected return', U])} vs {pct(rv.loc['expected return', S])}). "
    f"In the brief's recovery case (downside 2028 EBITDA × 6.0x) both bonds recover 100%, so expected losses are zero and the "
    f"comparison comes down to yield. The secured notes have a 7.125% coupon but trade above their call price: at 104.10 their "
    f"yield-to-worst is {pct(ys['ytw'])} to the May 2027 call at 102. The unsecured notes at 97.47 yield {pct(yu['ytw'])} to "
    f"maturity. Two caveats matter. First, the secured price is a stale TRADEcho print from 19 June 2026, because the notes do not "
    f"trade on a German exchange. The call would only flip below a secured price of {R['px_flip']:.2f}. Second, the call depends "
    f"on recovery: below {R['m_flip']:.2f}x EBITDA the unsecured notes start to lose principal and the secured notes win.")
r.bullets([
    f"<b>Credit is improving.</b> Credit-agreement leverage fell from 7.1x (2022) to 4.2x (LTM June 2026). The April 2026 "
    f"refinancing pushed all bank debt to 2032–2033, and liquidity is {eur(H.loc['Liquidity (company)', 'LTM Jun-26'])}. "
    f"S&P upgraded Grifols to BB- (stable) in December 2025, and Moody's (B1) has a positive outlook.",
    f"<b>The 2028s can be refinanced, or simply repaid.</b> Our base case puts leverage at {rb['Net leverage Oct 2028 (x)']:.1f}x "
    f"at the October 2028 maturity and our downside case at {rd['Net leverage Oct 2028 (x)']:.1f}x. Cash, the undrawn revolver and "
    f"projected free cash flow cover the {eur(rb['Unsecured notes due Oct 2028'])} due {rb['Liquidity / notes due (x)']:.1f}x in "
    f"the base case and {rd['Liquidity / notes due (x)']:.1f}x in the downside. The revolver's springing maturity (mid-July 2028) "
    f"forces the issue early, which helps holders.",
    f"<b>Most of the secured coupon cannot be earned.</b> Grifols has already used the call: it redeemed €500m of the 7.5% "
    f"2030 notes at 104 in May 2026. The 7.125% notes become cheaper to call at 102 in May 2027 and at par in May 2028. Their "
    f"{pct(ys['ytm'])} yield to maturity is not available to a buyer at 104.10.",
])

# ---------------------------------------------------------------------------------------------------------------------
r.h1("1. Capital structure at 30 June 2026")
r.p("Grifols makes plasma-derived medicines (immunoglobulins, albumin, alpha-1) and diagnostics. Revenue was €7.5bn in 2025. "
    "The plasma business is capital-heavy: Grifols operated over 400 plasma collection centres at end-2025, and inventory turnover "
    "was 309 days at end-2023 (20-F 2025). The debt stack below is taken from the H1 2026 interim report, after the 14 April 2026 refinancing "
    "(new USD 2.0bn and €1.25bn term loans due 2033, a USD 2.065bn revolver due 2032, and the repayment of the 2019 notes) and the "
    "May 2026 partial redemption of the 7.5% notes.")
cs = M.CAP.copy()
yw = {n: v for n, v in Y.items()}
cs["Yield-to-worst"] = [pct(yw[n]["ytw"]) if n in yw else "" for n in cs["Instrument"]]
cs["Amount (EUR m)"] = cs["Amount (EUR m)"].map(lambda v: f"{v:,.0f}")
cs["Price"] = cs["Price"].map(lambda v: f"{v:.2f}" if v is not None and pd.notna(v) else "–")
cs = cs[["Instrument", "Amount (EUR m)", "Coupon", "Maturity", "Security", "Price", "Yield-to-worst", "Price source"]]
r.table(cs, caption="Table 1. Capital structure at 30 June 2026. Cash was €513m, so net financial debt as per the credit agreement "
        "was €7,798m and net secured debt €4,939m (2.7x). Ratings: S&P BB- (secured BB-, unsecured B); Fitch BB- (BB+ / B+); "
        "Moody's B1 positive (Ba3 / B3). Prices for the 2030 notes are stale TRADEcho prints, the 2028 euro notes are quoted on "
        "Börse Frankfurt (whose yield, 5.28%, matches ours), and the other instruments have no free quote.",
        index=False, col_widths=cmw([4.6, 1.5, 2.0, 1.7, 2.0, 1.1, 1.4, 3.6]), font=6.8)

# ---------------------------------------------------------------------------------------------------------------------
r.h1("2. Credit metrics, 2019 – LTM June 2026")
rows = ["Revenue", "Reported EBITDA", "Adjusted EBITDA (Credit Agreement)", "Net financial debt (Credit Agreement)",
        "Net leverage, Credit Agreement (x)", "Net leverage, reported (x)", "Net secured leverage, Credit Agreement (x)",
        "Adjusted EBITDA / cash interest (x)", "FCF (CFO − capex − leases)", "FCF / gross debt", "Liquidity (company)"]
t = H.loc[rows].copy()
fmt = {r_: (lambda v: f"{v:.1f}x") if "(x)" in r_ else (lambda v: f"{v * 100:.1f}%") if "/ gross" in r_ else (lambda v: f"{v:,.0f}")
       for r_ in rows}
t = pd.DataFrame({c: [fmt[i](t.loc[i, c]) if pd.notna(t.loc[i, c]) else "–" for i in rows] for c in t.columns}, index=rows)
t.index.name = "EUR m"
r.table(t, caption="Table 2. Credit metrics. Flows for LTM June 2026 = FY2025 + H1 2026 − H1 2025. Credit-agreement figures are the "
        "company's (results releases); reported leverage = balance-sheet financial debt including leases, less cash, divided by "
        "EBIT + D&A. Cash interest = interest paid. Sources: SEC XBRL company facts (20-F 2019–2024), FY2025 audited statements, "
        "H1 2026 report.", col_widths=cmw([5.6] + [1.45] * 8), font=6.8)
r.image(F / "fig_leverage.png", 15.5, "Figure 1. Leverage on three definitions, and the Gotham claim.")
r.h2("Reported EBITDA versus credit-agreement EBITDA")
br = pd.DataFrame({"EUR m": list(M.EBITDA_BRIDGE.values()) + [M.EBITDA_CA_LTM]},
                  index=list(M.EBITDA_BRIDGE.keys()) + ["Adjusted EBITDA as per Credit Agreement (company; rounding 1)"])
br["EUR m"] = br["EUR m"].map(lambda v: f"{v:,.0f}")
r.table(br, caption="Table 3. LTM June 2026 EBITDA bridge (H1 2026 results annex).", col_widths=cmw([11.0, 2.0]), font=7.2)
r.p(f"The covenant EBITDA of €1,863m is {M.EBITDA_CA_LTM / M.EBITDA_REPORTED_LTM - 1:.0%} above reported EBITDA. The biggest "
    f"add-back is €169m of <i>run-rate</i> cost savings and synergies expected over the next twelve months, which is "
    f"{169 / M.EBITDA_CA_LTM:.0%} of covenant EBITDA and has not yet been earned. The IFRS 16 deduction (−€120m) is legitimate. "
    f"It puts leases back as an operating cost, which is why lease liabilities (€1,045m) are left out of credit-agreement net debt. "
    f"On the reported basis, with leases as debt and no add-backs, leverage is {M.ND_BS_JUN26 / M.EBITDA_REPORTED_LTM:.1f}x rather "
    f"than 4.2x. That is the right number for comparing Grifols with peers. The bond covenants, however, use the indenture "
    f"definitions, so the debt-incurrence tests run on the covenant basis.")
r.h2("The Gotham City Research challenge (January 2024)")
p = R["prop"]
r.p(f"On 9 January 2024 Gotham City Research claimed that Grifols' leverage was 'closer to 10x–13x', not the ~6x it reported. "
    f"Gotham had two main points. First, Grifols fully consolidates Haema and BPC Plasma, which are owned by Scranton Enterprises, "
    f"a vehicle linked to Grifols' founding families. Second, Grifols fully consolidates Grifols Diagnostic Solutions, 45% of which "
    f"was sold to Shanghai RAAS. So 100% of their EBITDA counted while the minority owners' claims did not show up as debt. "
    f"Grifols rejected the report (6-Ks, 9–11 January 2024). Spain's market regulator, the CNMV, investigated and in September 2024 "
    f"opened a sanctioning procedure over financial information and alternative performance measures for 2021–2023 (20-F 2025, "
    f"Legal Proceedings). Grifols now publishes an annex on non-controlling interest (NCI) contributions, which lets us test the "
    f"point directly. Removing the minorities' share of credit-agreement EBITDA (€{M.EBITDA_CA_LTM - p['EBITDA']:,.0f}m) and of net "
    f"debt (GDS holds a €1,151m receivable from Grifols, so SRAAS's 45% share adds debt) gives "
    f"<b>{p['Leverage']:.1f}x proportionate leverage</b>. That is 0.5 turns above the headline 4.2x but far below Gotham's range. "
    f"Gotham's figures for 2023 are also not comparable with today's: 2022–2023 leverage was genuinely high (7.1x and 6.4x on the "
    f"company's own covenant basis; 8.6x reported).")

# ---------------------------------------------------------------------------------------------------------------------
r.h1("3. Covenant summary")
cov = pd.DataFrame([
    ["Ranking", "Senior secured, first lien shared pari passu with the term loans and revolver", "Senior unsecured; effectively junior to €5.5bn of secured debt"],
    ["Debt incurrence", "FCCR ≥ 2.00x for ratio debt; secured ratio debt only if secured leverage ≤ 4.50x. Credit facilities basket €5.0bn; capital leases $500m",
     "FCCR ≥ 2.00x. Credit facilities basket €4.5bn + €1.0bn; capital leases greater of $500m and 4% of total assets"],
    ["Restricted payments", "Builder: 50% of net income since 2019; unlimited if leverage ≤ 3.75x", "Same: 50% builder; unlimited if leverage ≤ 3.75x"],
    ["Asset sales", "Apply proceeds within 365 days; excess > $200m offered at the call price", "Apply within 365 days; excess > €300m offered at 100%"],
    ["Change of control", "Put at the call price (104% until Apr 2027); trigger > 35% held by a non-permitted holder or > 50% by the Permitted Holder Group",
     "Put at 101%; same triggers"],
    ["Call schedule", "104% from May 2026, 102% from May 2027, par from May 2028", "Par from 15 Oct 2026"],
    ["Maintenance test", "None (revolver only: 7.0x, tested if > 40% drawn)", "None"],
    ["Suspension", "Covenants fall away if two agencies rate it investment grade", "Same"],
], columns=["", "7.125% secured notes due 2030 (indenture 19 Dec 2024)", "3.875% unsecured notes due 2028 (indenture 5 Oct 2021)"])
r.table(cov, caption="Table 4. Covenant summary (indentures filed with SEC as exhibit 2.16 to the 2024 20-F and exhibit 2.9 to the "
        "2021 20-F; section references in the Excel model). FCCR = fixed-charge coverage ratio.", index=False,
        col_widths=cmw([2.6, 7.6, 7.6]), font=6.8)
r.p("For the comparison the covenants matter in three ways. (1) <b>Priming capacity.</b> The secured-leverage test (4.50x) and the "
    "€5.0–5.5bn credit-facilities baskets mean €5.5bn of secured debt could grow further ahead of the unsecured notes. This is "
    "a structural weakness for the 2028s, but only if they are still outstanding when the company is in trouble. "
    "(2) <b>Leakage.</b> Both indentures allow unlimited dividends once leverage is at or below 3.75x, which our base case reaches "
    "in 2027. That money comes out of the equity cushion that protects both bonds, and more so the unsecured. "
    "(3) <b>Change of control.</b> If one happened, it would pay the secured notes the call price, which is almost exactly their market price, "
    "and the unsecured notes 101, which is 3.5 points above theirs. This favours the 2028s.")

# ---------------------------------------------------------------------------------------------------------------------
r.h1("4. Projections 2026–2028 and the October 2028 maturity")
r.p(f"<b>Base case.</b> Revenue is flat in 2026 because of FX (reported revenue −2.8% in H1 2026, +2.6% at constant currency) and "
    f"grows 5% a year after that. The adjusted EBITDA margin is 25.0% / 25.5% / 26.0%, against guidance of at least 25% in 2026. "
    f"Capex (including IT and R&D), cash taxes, working capital and other items are held at 2025 levels "
    f"({eur(sum(M.FCF_ITEMS.values()))} a year). Dividends are €128m. Cash interest uses the post-refinancing stack at today's "
    f"SOFR ({pct(M.SOFR)}) and Euribor ({pct(M.EURIBOR)}): {eur(R['base'].loc['Cash interest', 2026])}. This gives 2026 FCF before "
    f"dividends of {eur(R['base'].loc['FCF pre-dividends', 2026])}, inside the company's guidance of €500–575m (pre-M&A). "
    f"<b>Downside case.</b> The brief asks for a margin 300bp lower and plasma cost per litre 10% higher. Grifols does not "
    f"disclose plasma's share of cost of sales, so the two can only be combined through an assumption. The 300bp cut equals a 10% "
    f"plasma-cost rise if plasma is {R['plasma_eq']:.0%} of cost of sales (cost of sales was 62.0% of 2025 revenue). We therefore "
    f"model one 300bp cut, half of it in H2 2026, and treat the two descriptions as the same shock.")
pj = pd.concat({"Base": R["base"], "Downside": R["down"]})
show = ["Revenue", "EBITDA margin", "Adjusted EBITDA", "Cash interest", "FCF pre-dividends", "Net debt (Credit Agreement)",
        "Net leverage (x)", "EBITDA / cash interest (x)"]
tbl = {}
for case in ["Base", "Downside"]:
    for i in show:
        v = pj.loc[(case, i)]
        tbl[(case, i)] = [f"{x * 100:.1f}%" if i == "EBITDA margin" else f"{x:.2f}x" if "(x)" in i else f"{x:,.0f}" for x in v]
pt = pd.DataFrame(tbl, index=[2026, 2027, 2028]).T
pt.index = [f"{a}: {b}" for a, b in pt.index]
r.table(pt, caption="Table 5. Projections (EUR m). Credit-agreement EBITDA = adjusted EBITDA + €27m (the FY2025 difference).",
        col_widths=cmw([7.5, 2.2, 2.2, 2.2]), font=7.0)
r.image(F / "fig_projection.png", 14.5, "Figure 2. Credit-agreement leverage path; stars mark October 2028.")
ref = pd.DataFrame({"Base": rb, "Downside": rd}).drop("Leverage at or below 3.5x target")
ref = ref.apply(lambda c: [f"{v:.2f}x" if "(x)" in i else f"{v:,.0f}" for i, v in c.items()])
r.table(ref, caption="Table 6. Position at the October 2028 maturity of the unsecured notes (EUR m). Liquidity = cash and undrawn "
        "revolver at 30 June 2026 plus projected FCF after dividends to October 2028.", col_widths=cmw([8.0, 2.5, 2.5]), font=7.2)
r.p(f"<b>Can the 2028s be refinanced?</b> Yes, in both cases. Base-case leverage of {rb['Net leverage Oct 2028 (x)']:.1f}x is below "
    f"the 3.5x target and below the 3.75x restricted-payments threshold, which is consistent with a BB rating. Even the downside "
    f"case ({rd['Net leverage Oct 2028 (x)']:.1f}x) is below the 4.3–4.6x at which Grifols issued the 7.125% notes (December "
    f"2024) and refinanced its bank debt (April 2026). Refinancing "
    f"is also not strictly needed: liquidity of {eur(rd['Liquidity available before maturity'])} in the downside case covers the "
    f"€2.0bn of notes {rd['Liquidity / notes due (x)']:.1f}x. The revolver's springing maturity (91 days before any unrefinanced "
    f"material maturity, i.e. mid-July 2028) means Grifols must deal with the notes by then, either from cash and revolver drawings "
    f"or with new bonds. The main risk is a market shut to high-yield issuers in H1 2028 combined with an operational shock large "
    f"enough to use up the revolver. That would also be the default scenario for the recovery analysis.")

# ---------------------------------------------------------------------------------------------------------------------
r.h1("5. Recovery waterfall (default in 2028)")
wd = R["w_down"]
wt = pd.DataFrame({"EUR m / %": [eur(e_down), "6.0x", eur(wd["EV"]), eur(wd["Admin claims"]), eur(wd["Secured claims"]),
                                 f"{wd['Secured recovery']:.0%}", eur(wd["Unsecured claims"]), f"{wd['Unsecured recovery']:.0%}",
                                 eur(wd["Residual to equity"])]},
                  index=["Downside 2028 adjusted EBITDA", "Multiple (brief)", "Enterprise value", "Administrative claims (5% of EV, assumption)",
                         "Secured claims: TLB €3,001m + RCF 80% drawn €1,451m + secured notes €2,100m", "Secured recovery",
                         "Unsecured claims: 2028 notes €2,019m + other financial liabilities €960m (incl. GIC €686m)",
                         "Unsecured recovery", "Residual to equity"])
r.table(wt, caption="Table 7. Waterfall following the brief. Leases are excluded because adjusted EBITDA is after lease payments.",
        col_widths=cmw([12.0, 2.5]), font=7.2)
r.p(f"At 6.0x the enterprise value ({eur(wd['EV'])}) covers all secured and unsecured claims, so <b>both bonds recover 100%</b>. "
    f"The brief's case is generous to creditors: a company that actually defaults has usually lost more EBITDA than our downside "
    f"assumes, and distressed sale multiples are lower than going-concern ones. Figure 3 shows how recovery depends on the multiple. Secured creditors are "
    f"covered down to {R['be_sec']:.2f}x and the unsecured notes down to {R['be_uns']:.2f}x. Below that, the unsecured notes lose "
    f"principal quickly because {eur(wd['Secured claims'])} of secured claims (with the revolver 80% drawn) sit ahead of them.")
r.image(F / "fig_recovery.png", 14.5, "Figure 3. Recovery by enterprise-value multiple; at 6.0x both recover in full.")

# ---------------------------------------------------------------------------------------------------------------------
r.h1("6. Relative value")
rt = pd.DataFrame({c: [f"{rv.loc['price', c]:.2f}", pct(rv.loc["YTM", c]), pct(rv.loc["YTW", c]), rv.loc["worst", c],
                       pct(rv.loc["Bund (matched)", c]), bp(rv.loc["spread", c]), f"{rv.loc['leverage through tranche (x)', c]:.2f}x",
                       f"{rv.loc['spread per turn (bp)', c]:.0f}bp", f"{rv.loc['recovery', c]:.0%}", pct(rv.loc["PD (3y cumulative)", c]),
                       pct(rv.loc["expected loss", c]), pct(rv.loc["expected return", c])] for c in [S, U]},
                  index=["Price", "Yield to maturity", "Yield-to-worst", "Worst date", "Bund, matching maturity (Bundesbank Svensson)",
                         "Spread over Bund", "Net leverage through the tranche", "Spread per turn of leverage", "Recovery (6.0x waterfall)",
                         "Default probability: S&P BB-, 3-year cumulative (1981–2024)", "Expected loss = PD × (1 − recovery)",
                         "Expected return = YTW − expected loss"])
r.table(rt, caption=f"Table 8. Relative value at settlement 9 October 2026. Gap = {bp(gap)} in favour of the unsecured notes. "
        f"For reference, the ICE BofA Euro High Yield index OAS was {pct(R['hy_oas'][0])} on {R['hy_oas'][1]}.",
        col_widths=cmw([8.3, 3.6, 3.6]), font=7.2)
r.image(F / "fig_yields.png", 14.0, "Figure 4. Yield to maturity, yield-to-worst and the matching Bund for each bond.")
r.p(f"<b>Reading the numbers.</b> Per turn of leverage the unsecured notes pay {rv.loc['spread per turn (bp)', U]:.0f}bp against "
    f"{rv.loc['spread per turn (bp)', S]:.0f}bp for the secured notes. Their spread of {bp(rv.loc['spread', U])} over a two-year Bund "
    f"is below the euro high-yield index ({bp(R['hy_oas'][0])}), which is reasonable for a short BB-/B bond that can be repaid from "
    f"liquidity. The secured notes' spread to their worst date ({bp(rv.loc['spread', S])}) is very thin because the price is "
    f"pinned near the call price. If they were never called, their {pct(ys['ytm'])} yield to maturity would beat the unsecured notes. "
    f"But Grifols has every reason to call a 7.125% coupon once the price reaches 102 (May 2027): its new euro term loan costs "
    f"Euribor + 3.00% (about 5.6%).")
r.h2("What would change the call")
r.bullets([
    f"<b>A lower secured price.</b> At {R['px_neutral']:.2f} the gap falls to −50bp (neutral) and at {R['px_flip']:.2f} it is zero. A "
    f"current executable price is the first thing to get. The last print is 3.5 months old and the notes are callable today at 104.",
    f"<b>A lower recovery multiple.</b> At {R['m_neutral']:.2f}x the result is neutral, and below {R['m_flip']:.2f}x the secured notes "
    f"win. That needs a distressed sale value 25% below the brief's 6.0x on already-reduced downside EBITDA.",
    "<b>Issue-level default risk.</b> The brief uses one issuer PD (BB-) for both bonds, as S&P's methodology does. S&P's lower "
    "unsecured issue rating (B) reflects recovery, which the waterfall already captures, so a separate PD would double-count.",
    "<b>Duration.</b> The unsecured notes run to October 2028; the secured notes will most likely be called in 2027. A holder of "
    "the secured notes faces reinvestment risk; a holder of the unsecured notes takes 1.5 more years of Grifols risk. That risk "
    "falls if the deleveraging plan is delivered.",
])

# ---------------------------------------------------------------------------------------------------------------------
r.h1("7. Risks and limitations")
r.bullets([
    "<b>Stale price.</b> The 7.125% and 7.5% 2030 notes trade over the counter. The only free prices are TRADEcho prints from "
    "19 June and 19 May 2026 (finanzen.net). Börse Frankfurt, the brief's source, has no page for these ISINs. The recommendation "
    "should be re-run with a dealer quote.",
    "<b>Plasma cost.</b> The downside treats '−300bp margin' and '+10% plasma cost per litre' as one shock, because the plasma "
    f"share of cost of sales is not disclosed. If plasma is more than {R['plasma_eq']:.0%} of cost of sales, a 10% rise costs "
    "more than 300bp.",
    "<b>Governance.</b> The Gotham episode, the founding families' related-party structures (Scranton) and the CNMV review "
    "remain overhangs. Proportionate leverage (4.7x) is the better measure of what creditors are owed against.",
    "<b>Assumptions held flat.</b> Capex, taxes, working capital and dividends are held at 2025 levels, and base rates at today's "
    "level. Interest does not fall as debt is repaid, which is conservative.",
    "<b>Default rates.</b> S&P's 2025 study is not freely available, so the PD comes from the 2024 study (1981–2024 average, BB- "
    "3-year 4.62%).",
    "<b>Recovery.</b> The waterfall is simplified. It ignores structural subordination between subsidiaries, collateral gaps "
    "(e.g. assets in China and Germany outside the security package) and the GIC liability's ranking.",
])
r.p("<b>Sources.</b> Grifols 20-F 2019–2025 and 6-K results releases (SEC EDGAR); indentures (20-F exhibits); H1 2026 interim "
    "report and results presentation; Grifols fixed-income page (ratings, 7 Oct 2026); Börse Frankfurt (XS2393001891); "
    "finanzen.net (XS2961445090, XS2805351843); Bundesbank yield curve (BBSIS); FRED (BAMLHE00EHYIOAS, SOFR, DEXUSEU); ECB "
    "(3-month Euribor); S&P 2024 Annual Global Corporate Default and Rating Transition Study. Model: model/grifols_credit_model.xlsx.")
r.build()
print("built", r.path if hasattr(r, "path") else "")
