"""Writes model/grifols_credit_model.xlsx. Inputs are blue on yellow; every derived number is an Excel formula.
src/check_workbook.py recalculates the file in LibreOffice and checks it against src/model.py.

    python src/build_workbook.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT)]
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as L

from src import model as M

OUT = ROOT / "model" / "grifols_credit_model.xlsx"
R = M.run()
BLUE, BOLD = Font(color="1F4E79"), Font(bold=True)
INPUT = PatternFill("solid", fgColor="FFF4D6")
HEAD = PatternFill("solid", fgColor="E8ECF2")
WRAP = Alignment(wrap_text=True, vertical="top")
wb = Workbook()


def sh(name, wa=48, w=13):
    ws = wb.create_sheet(name)
    ws.column_dimensions["A"].width = wa
    for c in range(2, 30):
        ws.column_dimensions[L(c)].width = w
    return ws


def inp(ws, ref, v, fmt=None):
    ws[ref] = v; ws[ref].font = BLUE; ws[ref].fill = INPUT
    if fmt:
        ws[ref].number_format = fmt


def put(ws, ref, v, fmt=None, bold=False):
    ws[ref] = v
    if fmt:
        ws[ref].number_format = fmt
    if bold:
        ws[ref].font = BOLD


def header(ws, row, labels, col=1):
    for j, h in enumerate(labels):
        c = ws.cell(row=row, column=col + j, value=h); c.font = BOLD; c.fill = HEAD; c.alignment = WRAP


# ---------------------------------------------------------------------------------------------------------------------
I = sh("Inputs", 70)
I["A1"] = "Grifols credit model — inputs (blue on yellow = input; everything else is a formula)"; I["A1"].font = BOLD
inputs = [
    ("settle", "Settlement date (trade 7 Oct 2026, T+2)", pd.Timestamp(M.SETTLE).to_pydatetime(), "yyyy-mm-dd"),
    ("fx", "EUR/USD at 30 Jun 2026 (USD 1,995m TLB = EUR 1,751m in the H1 2026 report)", M.EURUSD_JUN, "0.0000"),
    ("sofr", "SOFR, 6 Oct 2026 (FRED SOFR)", M.SOFR, "0.00%"),
    ("euribor", "3-month Euribor, Sep 2026 (ECB data portal)", M.EURIBOR, "0.00%"),
    ("fee", "RCF commitment fee on undrawn amount (ASSUMPTION)", 0.0035, "0.00%"),
    ("other_rate", "Interest rate on other loans and other financial liabilities (ASSUMPTION)", 0.05, "0.00%"),
    ("bund1", "Bund yield, residual maturity 1 year (Bundesbank Svensson, 7 Oct 2026)", R["bund"][1], "0.00%"),
    ("bund2", "Bund yield, residual maturity 2 years", R["bund"][2], "0.00%"),
    ("bund3", "Bund yield, residual maturity 3 years", R["bund"][3], "0.00%"),
    ("bund4", "Bund yield, residual maturity 4 years", R["bund"][4], "0.00%"),
    ("hyoas", f"ICE BofA Euro High Yield OAS ({R['hy_oas'][1]}, FRED BAMLHE00EHYIOAS)", R["hy_oas"][0], "0.00%"),
    ("pd3", "S&P BB- 3-year cumulative default rate, 1981–2024 (2024 default study)", R["sp"]["y3"], "0.00%"),
    ("mult", "Recovery: EV / downside 2028 EBITDA (brief)", M.MULTIPLE, "0.0x"),
    ("admin", "Recovery: administrative claims, % of EV (ASSUMPTION)", M.ADMIN, "0.0%"),
    ("rcfdraw", "Recovery: RCF drawn at default (brief)", 0.80, "0%"),
    ("thresh", "Recommendation: neutral band (brief)", 0.005, "0.00%"),
    ("down", "Downside: EBITDA margin cut (brief; half of it in 2026)", M.DOWNSIDE_BPS, "0.00%"),
    ("cogs", "Cost of sales / revenue 2025 (7,524 revenue; 4,665 cost of sales)", M.COGS_PCT_REV, "0.0%"),
    ("plasma_up", "Downside: plasma cost per litre increase (brief)", 0.10, "0%"),
    ("ca_uplift", "Credit-agreement EBITDA minus adjusted EBITDA, FY2025 (1,852 − 1,825)", M.CA_UPLIFT, "#,##0"),
    ("capex", "Capex, IT and capitalised R&D per year (2025: 531)", M.FCF_ITEMS["capex_it_rd"], "#,##0"),
    ("taxes", "Cash taxes per year (2025: 169)", M.FCF_ITEMS["taxes"], "#,##0"),
    ("nwc", "Working capital outflow per year (2025: 67)", M.FCF_ITEMS["nwc"], "#,##0"),
    ("others", "Other cash items per year (2025: 69)", M.FCF_ITEMS["others"], "#,##0"),
    ("divs", "Dividends paid per year (2025: 128)", M.DIVIDENDS, "#,##0"),
    ("nd25", "Net financial debt as per Credit Agreement, 31 Dec 2025", 7759.0, "#,##0"),
    ("nd_jun", "Net financial debt as per Credit Agreement, 30 Jun 2026", M.ND_CA_JUN26, "#,##0"),
    ("rev25", "Revenue 2025", 7524.0, "#,##0"),
    ("cash", "Cash, 30 Jun 2026", M.CASH_JUN26, "#,##0"),
]
REF = {}
for i, (k, lab, v, fmt) in enumerate(inputs):
    r = 3 + i
    I[f"A{r}"] = lab; inp(I, f"B{r}", v, fmt)
    REF[k] = f"Inputs!$B${r}"
r = 4 + len(inputs)
I[f"A{r}"] = "Base case (ASSUMPTION; 2026 = flat reported revenue after FX, H1 2026 −2.8%)"; I[f"A{r}"].font = BOLD
header(I, r + 1, ["", 2026, 2027, 2028])
I[f"A{r + 2}"] = "Revenue growth"; I[f"A{r + 3}"] = "Adjusted EBITDA margin"
for j, y in enumerate((2026, 2027, 2028)):
    inp(I, f"{L(2 + j)}{r + 2}", M.BASE["rev_growth"][y], "0.0%")
    inp(I, f"{L(2 + j)}{r + 3}", M.BASE["margin"][y], "0.0%")
GROW = {y: f"Inputs!${L(2 + j)}${r + 2}" for j, y in enumerate((2026, 2027, 2028))}
MARG = {y: f"Inputs!${L(2 + j)}${r + 3}" for j, y in enumerate((2026, 2027, 2028))}
r += 5
I[f"A{r}"] = "Plasma equivalence: share of cost of sales that plasma must be for +10% per litre to equal the 300bp margin cut"
put(I, f"B{r}", f"={REF['down']}/({REF['plasma_up']}*{REF['cogs']})", "0.0%", True)
I[f"A{r + 1}"] = ("Grifols does not disclose plasma cost as a share of cost of sales, so the downside uses the 300bp cut; "
                  "it equals a 10% plasma cost rise if plasma is this share of cost of sales.")

# ---------------------------------------------------------------------------------------------------------------------
C = sh("Capital structure", 46, 12)
C["A1"] = "Capital structure at 30 June 2026 (EUR m; H1 2026 interim report) and bond yields at settlement 9 Oct 2026"; C["A1"].font = BOLD
C["A2"] = ("Yields are annual-equivalent (Excel YIELD gives a semi-annual rate y; shown as (1+y/2)^2−1, the convention Börse Frankfurt "
           "quotes). Yield-to-worst = lowest of yield to maturity and yield to each call date.")
cols = ["Instrument", "Amount (EUR m)", "Coupon", "Maturity", "Security", "Rank", "Price", "Price source", "Coupon rate",
        "YTM", "Yield to call 24 Oct 2026", "Yield to call 1 May 2027", "Yield to call 1 May 2028", "Yield-to-worst", "Worst date"]
header(C, 4, cols)
C.column_dimensions["H"].width = 30
cap = M.CAP.copy()
CAPROW = {}
for i, row in cap.reset_index(drop=True).iterrows():
    r = 5 + i
    CAPROW[row["Instrument"]] = r
    C[f"A{r}"] = row["Instrument"]
    if "USD 705m" in row["Instrument"]:
        put(C, f"B{r}", f"=705/{REF['fx']}", "#,##0")
    elif "USD 1,995m" in row["Instrument"]:
        inp(C, f"B{r}", row["Amount (EUR m)"], "#,##0")
    else:
        inp(C, f"B{r}", row["Amount (EUR m)"], "#,##0")
    C[f"C{r}"] = row["Coupon"]; C[f"D{r}"] = row["Maturity"]; C[f"E{r}"] = row["Security"]; C[f"F{r}"] = row["Rank"]
    if row["Price"] is not None and pd.notna(row["Price"]):
        inp(C, f"G{r}", float(row["Price"]), "0.00")
    C[f"H{r}"] = row["Price source"]
    name = row["Instrument"]
    if name in M.CALLS and row["Price"] is not None:
        cpn = float(row["Coupon"].rstrip("%")) / 100
        inp(C, f"I{r}", cpn, "0.000%")
        y, mo, d = map(int, row["Maturity"].split("-"))
        put(C, f"J{r}", f"=(1+YIELD({REF['settle']},DATE({y},{mo},{d}),I{r},G{r},100,2,1)/2)^2-1", "0.00%")
        if "secured" in name and "unsecured" not in name:
            # 24 Oct 2026 call (earliest date after 15 days' notice) falls inside the current coupon period (1 May – 1 Nov 2026)
            put(C, f"K{r}", (f"=((104+I{r}*100/2*(DATE(2026,10,24)-DATE(2026,5,1))/184)/(G{r}+I{r}*100/2*({REF['settle']}-DATE(2026,5,1))/184))"
                             f"^(2*184/(DATE(2026,10,24)-{REF['settle']}))-1"), "0.00%")
            put(C, f"L{r}", f"=(1+YIELD({REF['settle']},DATE(2027,5,1),I{r},G{r},102,2,1)/2)^2-1", "0.00%")
            put(C, f"M{r}", f"=(1+YIELD({REF['settle']},DATE(2028,5,1),I{r},G{r},100,2,1)/2)^2-1", "0.00%")
            put(C, f"N{r}", f"=MIN(J{r}:M{r})", "0.00%", True)
            put(C, f"O{r}", f'=INDEX($J$4:$M$4,MATCH(N{r},J{r}:M{r},0))')
        else:
            C[f"K{r}"] = "price < call price: calls raise the yield"
            put(C, f"N{r}", f"=J{r}", "0.00%", True); C[f"O{r}"] = "YTM"
n_last = 4 + len(cap)
tot = n_last + 2
lines = [("Gross financial debt excl. leases", f'=SUMIF(E5:E{n_last},"<>Leases",B5:B{n_last})'),
         ("Gross financial debt incl. leases", f"=SUM(B5:B{n_last})"),
         ("Secured debt (RCF drawn + TLB + secured notes)", f'=SUMIF(E5:E{n_last},"Senior secured",B5:B{n_last})'),
         ("Cash and cash equivalents", f"={REF['cash']}"),
         ("Net secured debt", f"=B{tot + 2}-B{tot + 3}"),
         ("RCF commitment (USD 2,065m)", f"=2065/{REF['fx']}"),
         ("RCF undrawn", f"=B{tot + 5}-B{CAPROW['Revolving credit facility (USD 2,065m)']}"),
         ("Liquidity (cash + undrawn RCF)", f"=B{tot + 3}+B{tot + 6}")]
for i, (lab, f) in enumerate(lines):
    C[f"A{tot + i}"] = lab; put(C, f"B{tot + i}", f, "#,##0", True)
CS = {"secured_debt": f"'Capital structure'!$B${tot + 2}", "rcf_commit": f"'Capital structure'!$B${tot + 5}",
      "liquidity": f"'Capital structure'!$B${tot + 7}", "rcf_undrawn": f"'Capital structure'!$B${tot + 6}"}
A = lambda name: f"'Capital structure'!$B${CAPROW[name]}"
YTW = lambda name: f"'Capital structure'!$N${CAPROW[name]}"
C[f"A{tot + 9}"] = ("Notes: the 7.125% and 7.500% 2030 notes do not trade on a German exchange; their prices are the last TRADEcho prints "
                    "shown on finanzen.net (19 Jun and 19 May 2026) and are stale. The 3.875% 2028 notes are quoted on Börse Frankfurt "
                    "(7 Oct 2026; its yield 5.28% matches column J). The 4.75% USD notes have no free quote. "
                    "Other financial liabilities include EUR 686m owed under the 2018 GIC agreement on Biomat USA.")
C[f"A{tot + 9}"].alignment = WRAP
C.freeze_panes = "B5"

# ---------------------------------------------------------------------------------------------------------------------
H = sh("Credit metrics", 52, 11)
Hd = pd.read_csv(ROOT / "data" / "credit_history.csv", index_col=0)
H["A1"] = "Credit metrics 2019 – LTM June 2026 (EUR m; sources in data/credit_history_sources.csv and src/history.py)"; H["A1"].font = BOLD
header(H, 3, ["EUR m"] + list(Hd.columns))
raw = ["Revenue", "EBIT", "D&A", "Cash", "Non-current financial liabilities", "Current financial liabilities", "Interest paid",
       "Operating cash flow", "Capex PP&E", "Capex intangibles", "Lease payments", "Adjusted EBITDA (Credit Agreement)",
       "Net financial debt (Credit Agreement)", "Net secured debt (Credit Agreement)", "Liquidity (company)"]
HR = {}
for i, lab in enumerate(raw):
    r = 4 + i; HR[lab] = r; H[f"A{r}"] = lab
    for j, c in enumerate(Hd.columns):
        v = Hd.loc[lab, c]
        if pd.notna(v):
            inp(H, f"{L(2 + j)}{r}", float(v), "#,##0")
r = 5 + len(raw)
derived = [("Reported EBITDA (EBIT + D&A)", "={c}{EBIT}+{c}{D&A}", "#,##0"),
           ("Gross financial debt incl. leases", "={c}{Non-current financial liabilities}+{c}{Current financial liabilities}", "#,##0"),
           ("Net financial debt (balance sheet)", "={c}{GROSS}-{c}{Cash}", "#,##0"),
           ("Gross leverage, reported (x)", "={c}{GROSS}/{c}{REP}", "0.0x"),
           ("Net leverage, reported (x)", "={c}{NETBS}/{c}{REP}", "0.0x"),
           ("Net leverage, Credit Agreement (x)", "={c}{Net financial debt (Credit Agreement)}/{c}{Adjusted EBITDA (Credit Agreement)}", "0.0x"),
           ("Net secured leverage, Credit Agreement (x)", "=IF({c}{Net secured debt (Credit Agreement)}=\"\",\"\",{c}{Net secured debt (Credit Agreement)}/{c}{Adjusted EBITDA (Credit Agreement)})", "0.0x"),
           ("Credit-agreement EBITDA / reported EBITDA", "={c}{Adjusted EBITDA (Credit Agreement)}/{c}{REP}", "0.00x"),
           ("Adjusted EBITDA (CA) / cash interest (x)", "={c}{Adjusted EBITDA (Credit Agreement)}/{c}{Interest paid}", "0.0x"),
           ("FCF (CFO − capex − leases)", "={c}{Operating cash flow}-{c}{Capex PP&E}-{c}{Capex intangibles}-{c}{Lease payments}", "#,##0"),
           ("FCF / gross debt", "={c}{FCF}/{c}{GROSS}", "0.0%")]
keys = {"REP": r, "GROSS": r + 1, "NETBS": r + 2, "FCF": r + 9}
for i, (lab, f, fmt) in enumerate(derived):
    rr = r + i; H[f"A{rr}"] = lab; HR[lab] = rr
    for j, c in enumerate(Hd.columns):
        col = L(2 + j)
        ff = f
        for k, v in {**{k: HR[k] for k in raw}, **keys}.items():
            ff = ff.replace("{c}{" + k + "}", f"{col}{v}")
        if "Net secured" in lab and pd.isna(Hd.loc["Net secured debt (Credit Agreement)", c]):
            continue
        put(H, f"{col}{rr}", ff, fmt, "Credit Agreement (x)" in lab)
H[f"A{r + len(derived) + 1}"] = ("Credit-agreement leverage for 2019–2025 and LTM Jun-26 is the company's own ratio; here it is recomputed from its "
                                 "published numerator and denominator. 2022 and 2023 use the ratios as later restated (incl. Biotest).")
H[f"A{r + len(derived) + 1}"].alignment = WRAP
H.freeze_panes = "B4"
LTMC = L(1 + len(Hd.columns))

# ---------------------------------------------------------------------------------------------------------------------
E = sh("EBITDA and Gotham", 74, 14)
E["A1"] = "Reported EBITDA to credit-agreement EBITDA, LTM June 2026 (H1 2026 results annex)"; E["A1"].font = BOLD
for i, (lab, v) in enumerate(M.EBITDA_BRIDGE.items()):
    E[f"A{3 + i}"] = lab; inp(E, f"B{3 + i}", v, "#,##0")
b = 3 + len(M.EBITDA_BRIDGE)
E[f"A{b}"] = "Adjusted EBITDA as per Credit Agreement (sum; company shows 1,863, difference is rounding)"
put(E, f"B{b}", f"=SUM(B3:B{b - 1})", "#,##0", True)
E[f"A{b + 1}"] = "Adjustments as % of reported EBITDA"; put(E, f"B{b + 1}", f"=B{b}/B3-1", "0.0%")
E[f"A{b + 2}"] = "of which run-rate savings not yet earned, as % of credit-agreement EBITDA"; put(E, f"B{b + 2}", f"=B8/B{b}", "0.0%")
g = b + 4
E[f"A{g}"] = "Gotham City Research (9 Jan 2024) and a proportionate view of leverage"; E[f"A{g}"].font = BOLD
E[f"A{g + 1}"] = ("Gotham argued Grifols' leverage was 'closer to 10x–13x' rather than the reported ~6x, mainly because Grifols fully "
                  "consolidates Haema and BPC Plasma (owned by Scranton Enterprises, a vehicle linked to Grifols' founding families) and "
                  "Grifols Diagnostic Solutions (45% sold to SRAAS), so 100% of their EBITDA counts while the minorities' claims do not "
                  "show up as debt. Grifols rejected the report (6-Ks of 9–11 Jan 2024) and has since published an NCI annex. "
                  "The table below uses that annex to put leverage on Grifols' own share.")
E[f"A{g + 1}"].alignment = WRAP; E.row_dimensions[g + 1].height = 90
header(E, g + 3, ["LTM Q2 2026", "EBITDA (CA)", "Net debt (CA)", "Minority share", "Minority EBITDA", "Minority net debt"])
for i, (nm, row) in enumerate(M.NCI.iterrows()):
    rr = g + 4 + i
    E[f"A{rr}"] = nm
    inp(E, f"B{rr}", row["EBITDA (Credit Agreement)"], "#,##0"); inp(E, f"C{rr}", row["Net financial debt (Credit Agreement)"], "#,##0")
    inp(E, f"D{rr}", row["Minority share"], "0.0%")
    put(E, f"E{rr}", f"=B{rr}*D{rr}", "#,##0"); put(E, f"F{rr}", f"=C{rr}*D{rr}", "#,##0")
s = g + 4 + len(M.NCI)
E[f"A{s}"] = "Total minority share"; put(E, f"E{s}", f"=SUM(E{g + 4}:E{s - 1})", "#,##0", True); put(E, f"F{s}", f"=SUM(F{g + 4}:F{s - 1})", "#,##0", True)
rows = [("Credit-agreement EBITDA, group", f"={LTMC}{0}"), ("Net debt (Credit Agreement), group", None),
        ("Leverage, group (company ratio)", None), ("EBITDA attributable to Grifols (group − minority share)", None),
        ("Net debt attributable to Grifols (group − minority share)", None), ("Proportionate leverage (x)", None),
        ("Reported leverage: balance-sheet net debt incl. leases / reported EBITDA (x)", None)]
p = s + 2
E[f"A{p}"] = rows[0][0]; put(E, f"B{p}", f"='Credit metrics'!{LTMC}{HR['Adjusted EBITDA (Credit Agreement)']}", "#,##0")
E[f"A{p + 1}"] = rows[1][0]; put(E, f"B{p + 1}", f"='Credit metrics'!{LTMC}{HR['Net financial debt (Credit Agreement)']}", "#,##0")
E[f"A{p + 2}"] = rows[2][0]; put(E, f"B{p + 2}", f"=B{p + 1}/B{p}", "0.00x")
E[f"A{p + 3}"] = rows[3][0]; put(E, f"B{p + 3}", f"=B{p}-E{s}", "#,##0")
E[f"A{p + 4}"] = rows[4][0]; put(E, f"B{p + 4}", f"=B{p + 1}-F{s}", "#,##0")
E[f"A{p + 5}"] = rows[5][0]; put(E, f"B{p + 5}", f"=B{p + 4}/B{p + 3}", "0.00x", True)
E[f"A{p + 6}"] = rows[6][0]; put(E, f"B{p + 6}", f"='Credit metrics'!{LTMC}{HR['Net leverage, reported (x)']}", "0.00x")
E[f"A{p + 7}"] = ("GDS holds a EUR 1,151m receivable from Grifols, so its net debt is negative; removing SRAAS's 45% of it adds to "
                  "Grifols' debt. Even on this basis leverage is 4.7x, well below Gotham's 10x–13x.")
E[f"A{p + 7}"].alignment = WRAP
PROP = f"'EBITDA and Gotham'!$B${p + 5}"

# ---------------------------------------------------------------------------------------------------------------------
V = sh("Covenants", 26, 58)
V["A1"] = "Covenant summary (indentures filed as exhibits 2.16 to the 2024 20-F and 2.9 to the 2021 20-F)"; V["A1"].font = BOLD
header(V, 3, ["Covenant", "7.125% senior secured notes due 2030 (indenture 19 Dec 2024)", "3.875% senior unsecured notes due 2028 (indenture 5 Oct 2021)"])
cov = [
    ("Ranking and security", "Senior secured; first-lien security shared pari passu with the term loans and RCF; guaranteed by the main subsidiaries.",
     "Senior unsecured; guaranteed by the same subsidiaries; effectively junior to all secured debt to the value of the collateral."),
    ("Debt incurrence (s.4.09)", "Ratio debt if fixed-charge coverage ≥ 2.00x; secured ratio debt only if secured leverage ≤ 4.50x (permitted liens). "
     "Credit facilities basket EUR 5.0bn; capital leases/purchase money USD 500m; refinancing basket.",
     "Ratio debt if fixed-charge coverage ≥ 2.00x. Credit facilities (and securitisation) basket EUR 4.5bn + EUR 1.0bn; "
     "capital leases/purchase money greater of USD 500m and 4.0% of total assets; refinancing basket."),
    ("Restricted payments (s.4.10)", "Builder basket: 50% of consolidated net income since 1 Jan 2019 plus equity proceeds; unlimited payments while "
     "leverage ≤ 3.75x after the payment.", "Same structure: 50% of consolidated net income since 1 Jan 2019 builder; unlimited while leverage ≤ 3.75x."),
    ("Asset sales (s.4.12)", "Net proceeds to be applied within 365 days (repay secured debt or reinvest); excess proceeds above USD 200m must be "
     "offered to holders at at least the call price then applicable (s.3.07).",
     "Net proceeds to be applied within 365 days; excess proceeds above EUR 300m must be offered to holders at 100% of principal."),
    ("Change of control (s.4.18)", "Put at the s.3.07 call price then applicable (104% until 30 Apr 2027, 102% to 30 Apr 2028, then 100%). "
     "Triggered if a non-permitted holder owns > 35% of votes, or the Permitted Holder Group > 50%, or on a sale of substantially all assets.",
     "Put at 101% plus accrued interest. Same triggers (> 35% non-permitted holder; > 50% Permitted Holder Group; sale of substantially all assets)."),
    ("Optional redemption", "Callable from 1 May 2026 at 104%, from 1 May 2027 at 102%, from 1 May 2028 at 100% (15–60 days' notice).",
     "Callable at 100% since 15 Oct 2026 (101.938% from 2024, 100.969% from 2025)."),
    ("Maintenance covenant", "None in the notes. The RCF has a springing net leverage test of 7.0x, tested only when more than 40% is drawn.",
     "None in the notes."),
    ("Covenant suspension", "Most covenants fall away while two of Moody's, S&P and Fitch rate the notes investment grade.",
     "Same (Investment Grade Status from two of the three agencies)."),
    ("Refinancing link", "RCF maturity springs to 91 days before any unrefinanced material debt maturity, i.e. mid-July 2028 for the 2028 notes "
     "(20-F 2025, Item 5).", "The notes are that material debt: they must be refinanced or repaid by mid-July 2028 to keep the RCF."),
]
for i, (k, a, b_) in enumerate(cov):
    rr = 4 + i
    V[f"A{rr}"] = k; V[f"A{rr}"].font = BOLD
    V[f"B{rr}"] = a; V[f"C{rr}"] = b_
    for c in "ABC":
        V[f"{c}{rr}"].alignment = WRAP
    V.row_dimensions[rr].height = 75
V.column_dimensions["B"].width = 62; V.column_dimensions["C"].width = 62

# ---------------------------------------------------------------------------------------------------------------------
P = sh("Projections", 46, 12)
P["A1"] = "Projections 2026–2028 (EUR m)"; P["A1"].font = BOLD
P["A2"] = ("Cash interest is the 30 June 2026 debt stack at current base rates: USD TLB SOFR+2.50%, EUR TLB Euribor+3.00%, RCF drawn "
           "SOFR+2.00% plus fee on the undrawn amount, notes at their coupons, other debt at the assumed rate.")
YC = {2026: "C", 2027: "D", 2028: "E"}
labels = ["Revenue", "Adjusted EBITDA margin", "Adjusted EBITDA", "Cash interest", "Capex, IT & R&D", "Taxes", "Working capital", "Other",
          "FCF before dividends", "Dividends", "Net debt (Credit Agreement), year end", "Credit-agreement EBITDA", "Net leverage (x)",
          "Adjusted EBITDA / cash interest (x)"]
interest = (f"=1751*({REF['sofr']}+0.025)+1250*({REF['euribor']}+0.03)+{A('Revolving credit facility (USD 2,065m)')}*({REF['sofr']}+0.02)"
            f"+({CS['rcf_commit']}-{A('Revolving credit facility (USD 2,065m)')})*{REF['fee']}"
            f"+{A('7.500% senior secured notes')}*0.075+{A('7.125% senior secured notes')}*0.07125+{A('3.875% senior unsecured notes')}*0.03875"
            f"+{A('4.750% senior unsecured notes (USD 705m)')}*0.0475+({A('Other loans')}+{A('Other financial liabilities (mainly GIC agreement)')})*{REF['other_rate']}")
PR = {}
for blk, (title, down) in enumerate([("Base case", False), ("Downside case (margin −300bp; equal to +10% plasma cost per litre if plasma "
                                                              "is the share of cost of sales on the Inputs sheet)", True)]):
    top = 4 + blk * 18
    P[f"A{top}"] = title; P[f"A{top}"].font = BOLD
    for y, c in YC.items():
        put(P, f"{c}{top}", y, None, True)
    rr = {l: top + 1 + i for i, l in enumerate(labels)}
    for l, r_ in rr.items():
        P[f"A{r_}"] = l
    for y, c in YC.items():
        prev = REF["rev25"] if y == 2026 else f"{YC[y - 1]}{rr['Revenue']}"
        put(P, f"{c}{rr['Revenue']}", f"={prev}*(1+{GROW[y]})", "#,##0")
        cut = f"-{REF['down']}*{0.5 if y == 2026 else 1}" if down else ""
        put(P, f"{c}{rr['Adjusted EBITDA margin']}", f"={MARG[y]}{cut}", "0.0%")
        put(P, f"{c}{rr['Adjusted EBITDA']}", f"={c}{rr['Revenue']}*{c}{rr['Adjusted EBITDA margin']}", "#,##0")
        put(P, f"{c}{rr['Cash interest']}", interest, "#,##0")
        for l, k in [("Capex, IT & R&D", "capex"), ("Taxes", "taxes"), ("Working capital", "nwc"), ("Other", "others"), ("Dividends", "divs")]:
            put(P, f"{c}{rr[l]}", f"={REF[k]}", "#,##0")
        put(P, f"{c}{rr['FCF before dividends']}", f"={c}{rr['Adjusted EBITDA']}-SUM({c}{rr['Cash interest']}:{c}{rr['Other']})", "#,##0", True)
        nd_prev = REF["nd25"] if y == 2026 else f"{YC[y - 1]}{rr['Net debt (Credit Agreement), year end']}"
        put(P, f"{c}{rr['Net debt (Credit Agreement), year end']}", f"={nd_prev}-({c}{rr['FCF before dividends']}-{c}{rr['Dividends']})", "#,##0")
        put(P, f"{c}{rr['Credit-agreement EBITDA']}", f"={c}{rr['Adjusted EBITDA']}+{REF['ca_uplift']}", "#,##0")
        put(P, f"{c}{rr['Net leverage (x)']}", f"={c}{rr['Net debt (Credit Agreement), year end']}/{c}{rr['Credit-agreement EBITDA']}", "0.00x", True)
        put(P, f"{c}{rr['Adjusted EBITDA / cash interest (x)']}", f"={c}{rr['Adjusted EBITDA']}/{c}{rr['Cash interest']}", "0.00x")
    PR[down] = rr
r0 = 4 + 2 * 18
P[f"A{r0}"] = "At the October 2028 maturity of the unsecured notes (10/12 of the way through 2028)"; P[f"A{r0}"].font = BOLD
header(P, r0 + 1, ["", "Base", "Downside"])
ref_lines = ["Net debt (Credit Agreement)", "Credit-agreement EBITDA (LTM)", "Net leverage (x)", "Unsecured notes due (EUR + USD)",
             "Cash + undrawn RCF, 30 Jun 2026", "FCF after dividends, Jul 2026 – Oct 2028", "Liquidity available before maturity",
             "Liquidity / notes due (x)", "Leverage at or below the 3.5x target?"]
REFI = {}
for i, l in enumerate(ref_lines):
    P[f"A{r0 + 2 + i}"] = l
for j, down in enumerate([False, True]):
    c = "BC"[j]; rr = PR[down]; base = r0 + 2
    nd = f"D{rr['Net debt (Credit Agreement), year end']}+10/12*(E{rr['Net debt (Credit Agreement), year end']}-D{rr['Net debt (Credit Agreement), year end']})"
    eb = f"D{rr['Credit-agreement EBITDA']}+10/12*(E{rr['Credit-agreement EBITDA']}-D{rr['Credit-agreement EBITDA']})"
    put(P, f"{c}{base}", f"={nd}", "#,##0"); put(P, f"{c}{base + 1}", f"={eb}", "#,##0")
    put(P, f"{c}{base + 2}", f"={c}{base}/{c}{base + 1}", "0.00x", True)
    put(P, f"{c}{base + 3}", f"={A('3.875% senior unsecured notes')}+{A('4.750% senior unsecured notes (USD 705m)')}", "#,##0")
    put(P, f"{c}{base + 4}", f"={REF['cash']}+{CS['rcf_undrawn']}", "#,##0")
    put(P, f"{c}{base + 5}", f"={REF['nd_jun']}-{c}{base}", "#,##0")
    put(P, f"{c}{base + 6}", f"={c}{base + 4}+{c}{base + 5}", "#,##0")
    put(P, f"{c}{base + 7}", f"={c}{base + 6}/{c}{base + 3}", "0.00x", True)
    put(P, f"{c}{base + 8}", f'=IF({c}{base + 2}<=3.5,"Yes","No")')
    REFI[down] = base
P[f"A{r0 + 12}"] = "Reading: refinancing needs market access at the leverage shown; liquidity alone also covers the notes in both cases."

# ---------------------------------------------------------------------------------------------------------------------
W = sh("Recovery", 58, 12)
W["A1"] = "Recovery waterfall: default in 2028, EV = downside 2028 adjusted EBITDA × multiple (brief)"; W["A1"].font = BOLD
dr = PR[True]
wl = [("Downside 2028 adjusted EBITDA", f"=Projections!E{dr['Adjusted EBITDA']}", "#,##0"),
      ("EV / EBITDA multiple", f"={REF['mult']}", "0.0x"),
      ("Enterprise value", "=B3*B4", "#,##0"),
      ("Administrative claims", f"=B5*{REF['admin']}", "#,##0"),
      ("Value for secured creditors", "=B5-B6", "#,##0"),
      ("Term loans (USD 1,751 + EUR 1,250)", f"={A('Term Loan B (USD 1,995m)')}+{A('Term Loan B (EUR)')}", "#,##0"),
      ("RCF at 80% drawn", f"={REF['rcfdraw']}*{CS['rcf_commit']}", "#,##0"),
      ("Secured notes (7.125% + 7.500%)", f"={A('7.125% senior secured notes')}+{A('7.500% senior secured notes')}", "#,##0"),
      ("Secured claims", "=SUM(B8:B10)", "#,##0"),
      ("Secured recovery", "=MIN(1,B7/B11)", "0.0%"),
      ("Value left after secured", "=MAX(0,B7-B11)", "#,##0"),
      ("Unsecured notes (3.875% + 4.750%)", f"={A('3.875% senior unsecured notes')}+{A('4.750% senior unsecured notes (USD 705m)')}", "#,##0"),
      ("Other unsecured financial claims (other loans, GIC liability)", f"={A('Other loans')}+{A('Other financial liabilities (mainly GIC agreement)')}", "#,##0"),
      ("Secured deficiency claim (shares with unsecured)", "=B11*(1-B12)", "#,##0"),
      ("Unsecured claims", "=SUM(B14:B16)", "#,##0"),
      ("Unsecured recovery", "=IF(B17=0,0,MIN(1,B13/B17))", "0.0%"),
      ("Residual to equity", "=MAX(0,B13-B17)", "#,##0")]
for i, (l, f, fmt) in enumerate(wl):
    W[f"A{3 + i}"] = l; put(W, f"B{3 + i}", f, fmt, "recovery" in l)
W["A23"] = "Leases are excluded from claims because adjusted EBITDA is after lease payments (IFRS 16 reversed)."
W["A25"] = "Sensitivity: recovery by EV multiple"; W["A25"].font = BOLD
header(W, 26, ["Multiple", "EV", "Secured recovery", "Unsecured recovery"])
for i, m in enumerate([3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5]):
    rr = 27 + i
    inp(W, f"A{rr}", m, "0.0x")
    put(W, f"B{rr}", f"=$B$3*A{rr}", "#,##0")
    left = f"$B$3*A{rr}*(1-{REF['admin']})"
    put(W, f"C{rr}", f"=MIN(1,{left}/$B$11)", "0.0%")
    put(W, f"D{rr}", f"=MIN(1,MAX(0,{left}-$B$11)/($B$14+$B$15+$B$11*(1-C{rr})))", "0.0%")
W["A36"] = "Lowest multiple with full secured recovery"; put(W, "B36", f"=$B$11/(1-{REF['admin']})/$B$3", "0.00x")
W["A37"] = "Lowest multiple with full unsecured recovery"; put(W, "B37", f"=($B$11+$B$14+$B$15)/(1-{REF['admin']})/$B$3", "0.00x")

# ---------------------------------------------------------------------------------------------------------------------
X = sh("Relative value", 52, 22)
X["A1"] = "Relative value and recommendation"; X["A1"].font = BOLD
header(X, 3, ["", "7.125% secured 2030", "3.875% unsecured 2028"])
sec, uns = "7.125% senior secured notes", "3.875% senior unsecured notes"
wd = {sec: "DATE(2027,5,1)", uns: "DATE(2028,10,15)"}
bund = lambda c: (f"=IF({c}6<=1,{REF['bund1']},IF({c}6<=2,{REF['bund1']}+({c}6-1)*({REF['bund2']}-{REF['bund1']}),"
                  f"IF({c}6<=3,{REF['bund2']}+({c}6-2)*({REF['bund3']}-{REF['bund2']}),{REF['bund3']}+({c}6-3)*({REF['bund4']}-{REF['bund3']}))))")
xl = ["Price", "Yield-to-worst", "Years to worst date", "Bund yield, matching maturity", "Spread over Bund", "Net leverage through the tranche (x)",
      "Spread per turn of leverage (bp)", "Recovery (waterfall)", "Default probability (S&P BB-, 3-year cumulative)",
      "Expected loss = PD × (1 − recovery)", "Expected return = YTW − expected loss"]
for i, l in enumerate(xl):
    X[f"A{4 + i}"] = l
for c, nm in [("B", sec), ("C", uns)]:
    put(X, f"{c}4", f"='Capital structure'!$G${CAPROW[nm]}", "0.00")
    put(X, f"{c}5", f"={YTW(nm)}", "0.00%")
    put(X, f"{c}6", f"=({wd[nm]}-{REF['settle']})/365.25", "0.00")
    put(X, f"{c}7", bund(c), "0.00%")
    put(X, f"{c}8", f"={c}5-{c}7", "0.00%")
    put(X, f"{c}10", f"={c}8*10000/{c}9", "0.0")
    put(X, f"{c}12", f"={REF['pd3']}", "0.00%")
    put(X, f"{c}13", f"={c}12*(1-{c}11)", "0.00%")
    put(X, f"{c}14", f"={c}5-{c}13", "0.00%", True)
put(X, "B9", f"='Credit metrics'!{LTMC}{HR['Net secured leverage, Credit Agreement (x)']}", "0.0x")
put(X, "C9", f"='Credit metrics'!{LTMC}{HR['Net leverage, Credit Agreement (x)']}", "0.0x")
put(X, "B11", "=Recovery!B14", "0.0%")
X["B11"] = "=Recovery!B12"; X["B11"].number_format = "0.0%"
put(X, "C11", "=Recovery!B18", "0.0%")
X["A16"] = "Gap: secured − unsecured expected return"; put(X, "B16", "=B14-C14", "0.00%", True)
X["A17"] = "Recommendation (brief's rule)"
put(X, "B17", (f'=IF(ABS(B16)<{REF["thresh"]},"Neutral on both (gap under 50bp)",IF(B16>0,'
               f'"Overweight the 7.125% secured 2030s, Underweight the 3.875% unsecured 2028s",'
               f'"Overweight the 3.875% unsecured 2028s, Underweight the 7.125% secured 2030s"))'), None, True)
X["A19"] = "Context"; X["A19"].font = BOLD
X["A20"] = "ICE BofA Euro High Yield index OAS"; put(X, "B20", f"={REF['hyoas']}", "0.00%")
X["A21"] = "Yield to maturity of the secured notes (if never called)"; put(X, "B21", f"='Capital structure'!$J${CAPROW[sec]}", "0.00%")
X["A22"] = "Proportionate leverage (EBITDA and Gotham sheet)"; put(X, "B22", f"={PROP}", "0.00x")
X["A24"] = "Sensitivities (values from src/model.py; solved by bisection)"; X["A24"].font = BOLD
sens = [("Secured price at which the gap is −50bp (neutral band edge)", R["px_neutral"], "0.00"),
        ("Secured price at which the gap is zero", R["px_flip"], "0.00"),
        ("EV multiple at which the gap is −50bp", R["m_neutral"], "0.00x"),
        ("EV multiple at which the gap is zero", R["m_flip"], "0.00x")]
for i, (l, v, fmt) in enumerate(sens):
    X[f"A{25 + i}"] = l; inp(X, f"B{25 + i}", float(v), fmt)

del wb["Sheet"]
OUT.parent.mkdir(exist_ok=True)
wb.save(OUT)
print("wrote", OUT)
