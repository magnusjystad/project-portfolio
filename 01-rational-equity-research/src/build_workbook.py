"""Writes model/rational_model.xlsx: every forecast and valuation number is an Excel formula driven by the Inputs
and History sheets, so the workbook can be audited and changed in Excel. src/model.py is the Python reference;
src/check_workbook.py recalculates the workbook with LibreOffice and checks the two agree.

    python src/build_workbook.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L

from src import model as M
from src.comps import comps_table

OUT = ROOT / "model" / "rational_model.xlsx"
BLUE = Font(color="1F4E79")                      # hard-coded inputs
BOLD = Font(bold=True)
HEAD = PatternFill("solid", fgColor="E8ECF2")
INPUT = PatternFill("solid", fgColor="FFF4D6")
THIN = Border(bottom=Side(style="thin", color="5A6B85"))
PCT, NUM, NUM2, EUR = "0.0%", "#,##0.0", "#,##0.00", "€#,##0.00"
YC = {y: L(3 + i) for i, y in enumerate(M.YEARS)}        # forecast years in columns C..L
HC = {y: L(3 + i) for i, y in enumerate(M.HIST)}         # history years in columns C..L

wb = Workbook()


def sheet(name, widths=None):
    ws = wb.create_sheet(name)
    ws.column_dimensions["A"].width = 46
    ws.column_dimensions["B"].width = 14
    for c in range(3, 16):
        ws.column_dimensions[L(c)].width = 11
    return ws


def put(ws, ref, v, fmt=None, font=None, fill=None):
    ws[ref] = v
    if fmt:
        ws[ref].number_format = fmt
    if font:
        ws[ref].font = font
    if fill:
        ws[ref].fill = fill
    return ref


def header(ws, row, label, cols):
    ws.cell(row=row, column=1, value=label).font = BOLD
    for col, txt in cols.items():
        c = ws[f"{col}{row}"]; c.value = txt; c.font = BOLD; c.fill = HEAD; c.alignment = Alignment(horizontal="right")
    ws.cell(row=row, column=1).fill = HEAD


# ---------------------------------------------------------------------------------------------------------------------
# Inputs
mk = M.market_inputs()
items, ncash = M.net_cash()
I = sheet("Inputs")
I["A1"] = "Rational AG — model inputs"; I["A1"].font = Font(bold=True, size=14)
I["A2"] = "Blue cells on a yellow background are inputs; everything else in the workbook is a formula."
rows = [
    ("Publication date", M.PUB.to_pydatetime(), "yyyy-mm-dd", "Report date"),
    ("Share price (EUR)", mk["price"], EUR, f"Xetra RAA close {mk['price_date']}, yfinance"),
    ("Shares outstanding (m)", M.SHARES, NUM2, "AR 2025 / H1 2026 report: 11,370,000 shares"),
    ("Risk-free rate: 10-year Bund yield", mk["rf"], "0.00%", f"Deutsche Bundesbank daily series, {mk['rf_date']}"),
    ("Equity risk premium (mature market, implied)", mk["erp"], "0.00%", f"Damodaran ERPbymonth.xlsx, {mk['erp_month']} (T12m, sustainable payout)"),
    ("Raw beta vs STOXX Europe 600 (60 monthly returns)", mk["beta_raw"], "0.000", "yfinance RAA.DE vs ^STOXX, Oct 2021 – Sep 2026; notebook"),
    ("Blume-adjusted beta", "=0.67*B9+0.33", "0.000", "0.67 × raw + 0.33"),
    ("Cost of equity = WACC (net cash)", "=B7+B10*B8", "0.00%", "CAPM"),
    ("Terminal growth", M.G_TERM, "0.0%", "Brief"),
    ("Tax rate on EBIT", M.COMMON["tax"], "0.0%", "Assumption: 2023–2025 effective rates 24.0%, 23.1%, 25.6%"),
    ("D&A, % of sales", M.COMMON["da"], "0.0%", "Assumption: 2022–2025 2.9–3.1%"),
    ("Capex, % of sales, 2026–2027", M.COMMON["capex"][2026], "0.0%", "Assumption: new service-parts building (H1 2026 capex €16.5m vs €9.1m)"),
    ("Capex, % of sales, 2028+", M.COMMON["capex"]["later"], "0.0%", "Assumption: 2023–2025 2.6–3.1%"),
    ("Net working capital, % of sales", M.COMMON["nwc"], "0.0%", "Assumption: 2021–2025 average 22.8%"),
    ("Lease payments, % of sales", M.COMMON["lease"], "0.0%", "Assumption: 2025 0.94%"),
    ("Dividend payout ratio", M.COMMON["payout"], "0.0%", "Company policy ~70% (H1 2026 report)"),
    ("FY2026 share of FCFF after 30 June 2026", 0.5, "0.0%", "H2 2026 cash flow is not in the 30 June net cash"),
]
r0 = 5
for i, (lab, v, fmt, src) in enumerate(rows):
    r = r0 + i
    I.cell(row=r, column=1, value=lab)
    c = I.cell(row=r, column=2, value=v); c.number_format = fmt
    if not (isinstance(v, str) and v.startswith("=")):
        c.font = BLUE; c.fill = INPUT
    I.cell(row=r, column=3, value=src).font = Font(italic=True, color="666666")
REF = {"date": "Inputs!$B$5", "price": "Inputs!$B$6", "shares": "Inputs!$B$7", "rf": "Inputs!$B$8", "erp": "Inputs!$B$9",
       "beta_raw": "Inputs!$B$10", "beta": "Inputs!$B$11", "ke": "Inputs!$B$12", "g": "Inputs!$B$13", "tax": "Inputs!$B$14",
       "da": "Inputs!$B$15", "capex1": "Inputs!$B$16", "capex2": "Inputs!$B$17", "nwc": "Inputs!$B$18", "lease": "Inputs!$B$19",
       "payout": "Inputs!$B$20", "h2": "Inputs!$B$21"}
# fix the formula references (rows shifted by r0)
I["B11"] = "=0.67*B10+0.33"; I["B12"] = "=B8+B11*B9"
# net cash
r = 24
I.cell(row=r, column=1, value="Net cash at 30 June 2026 (EUR m)").font = BOLD
for j, (k, v) in enumerate(items.items(), 1):
    I.cell(row=r + j, column=1, value=k)
    c = I.cell(row=r + j, column=2, value=round(v, 3)); c.number_format = NUM; c.font = BLUE; c.fill = INPUT
    I.cell(row=r + j, column=3, value="H1 2026 report").font = Font(italic=True, color="666666")
nc_last = r + len(items)
I.cell(row=nc_last + 1, column=1, value="Net cash").font = BOLD
I.cell(row=nc_last + 1, column=2, value=f"=SUM(B{r + 1}:B{nc_last})").number_format = NUM
REF["ncash"] = f"Inputs!$B${nc_last + 1}"
I.cell(row=nc_last + 2, column=3, value="Company: 'around 430 million euros in net financial assets' (H1 2026 report)").font = Font(italic=True, color="666666")

# Scenario assumptions
r = nc_last + 5
I.cell(row=r, column=1, value="Scenario assumptions").font = BOLD
header(I, r + 1, "", {"B": "Weight", "C": "Bear", "D": "Base", "E": "Bull"})
SC = ["Bear", "Base", "Bull"]
SCOL = {"Bear": "C", "Base": "D", "Bull": "E"}
I.cell(row=r + 2, column=1, value="Scenario weight")
for s in SC:
    c = I[f"{SCOL[s]}{r + 2}"]; c.value = M.WEIGHTS[s]; c.number_format = "0%"; c.font = BLUE; c.fill = INPUT
srow = {}
spec = [("Growth shift vs base, 2026", "growth_shift_2026"), ("Growth shift vs base, 2027–2030", "growth_shift"),
        ("EBIT margin 2026", ("margin", 2026)), ("EBIT margin 2027", ("margin", 2027)), ("EBIT margin 2028–2035", ("margin", "later")),
        ("iVario share step per year, 2026–2030", ("ivario_step", 0)), ("iVario share step per year, 2031–2035", ("ivario_step", 1))]
for k, (lab, key) in enumerate(spec):
    rr = r + 3 + k
    I.cell(row=rr, column=1, value=lab)
    for s in SC:
        a = M.ASSUMPTIONS[s]
        v = a[key] if isinstance(key, str) else a[key[0]][key[1]]
        c = I[f"{SCOL[s]}{rr}"]; c.value = v; c.number_format = "0.0%" if "margin" in lab or "shift" in lab else "0.00%"
        c.font = BLUE; c.fill = INPUT
    srow[lab] = rr
WROW = r + 2
r = r + 3 + len(spec) + 2
I.cell(row=r, column=1, value="Base-case regional sales growth").font = BOLD
header(I, r + 1, "", {"B": "2026", "C": "2027–2030", "D": "2035 (fade to)"})
GROW = {}
for k, reg in enumerate(M.REGIONS):
    rr = r + 2 + k
    I.cell(row=rr, column=1, value=reg)
    g26, g27 = M.BASE_GROWTH[reg]
    for col, v in [("B", g26), ("C", g27), ("D", M.FADE_TO)]:
        c = I[f"{col}{rr}"]; c.value = v; c.number_format = "0.0%"; c.font = BLUE; c.fill = INPUT
    GROW[reg] = rr
I.cell(row=r + 2 + len(M.REGIONS), column=3, value="2031–2035: linear fade from the 2027–2030 rate to the 2035 rate").font = Font(italic=True, color="666666")
for col in "BCDE":
    I.column_dimensions[col].width = 14
I.column_dimensions["C"].width = 70

# ---------------------------------------------------------------------------------------------------------------------
# History
H = M.history(); RH = M.regions_history(); PH = M.products_history()
S = sheet("History")
S["A1"] = "Reported history, EUR m (annual reports 2016–2025; see data/extract_*.csv for page references)"; S["A1"].font = BOLD
header(S, 3, "Income statement", {HC[y]: y for y in M.HIST})
IS = ["Sales revenues", "Cost of sales", "Gross profit", "Sales and service expenses", "R&D expenses", "G&A expenses",
      "Other operating income", "Other operating expenses", "EBIT", "Interest income", "Interest expenses", "EBT", "Income taxes", "Net profit"]
BS = ["Intangible assets", "PP&E", "Inventories", "Trade receivables", "Fixed deposits > 3 months", "Other current financial assets", "Cash", "Total assets",
      "Equity", "Pensions", "Trade payables", "Total equity and liabilities"]
CF = ["CFO", "Capex", "D&A", "Lease payments", "Dividends paid"]
HR = {}
row = 4


def hist_block(names, start):
    rr = start
    for n in names:
        S.cell(row=rr, column=1, value=n)
        for y in M.HIST:
            v = H.loc[n, y] if n in H.index else None
            if v is not None and pd.notna(v):
                c = S[f"{HC[y]}{rr}"]; c.value = round(float(v), 3); c.number_format = NUM; c.font = BLUE
        HR[n] = rr
        rr += 1
    return rr


row = hist_block(IS, 4)
header(S, row + 1, "Balance sheet (31 Dec)", {HC[y]: y for y in M.HIST})
row = hist_block(BS, row + 2)
header(S, row + 1, "Cash flow", {HC[y]: y for y in M.HIST})
row = hist_block(CF, row + 2)
header(S, row + 1, "Sales by customer region", {HC[y]: y for y in M.HIST})
row += 2
for reg in M.REGIONS:
    S.cell(row=row, column=1, value=reg + (" (incl. Latin America)" if reg == "Rest of world" else ""))
    for y in M.HIST:
        c = S[f"{HC[y]}{row}"]; c.value = round(float(RH.loc[y, reg]), 3); c.number_format = NUM; c.font = BLUE
    HR["reg_" + reg] = row; row += 1
S.cell(row=row, column=1, value="Check: regions − sales")
for y in M.HIST:
    S[f"{HC[y]}{row}"] = f"=SUM({HC[y]}{HR['reg_Germany']}:{HC[y]}{row - 1})-{HC[y]}{HR['Sales revenues']}"; S[f"{HC[y]}{row}"].number_format = NUM
row += 2
header(S, row, "Sales by product group", {HC[y]: y for y in M.HIST})
row += 1
S.cell(row=row, column=1, value="iVario")
for y in M.HIST:
    c = S[f"{HC[y]}{row}"]; c.value = round(float(PH.loc[y, "iVario"]), 3); c.number_format = NUM; c.font = BLUE
HR["iVario"] = row; row += 1
S.cell(row=row, column=1, value="iCombi (= sales − iVario)")
for y in M.HIST:
    S[f"{HC[y]}{row}"] = f"={HC[y]}{HR['Sales revenues']}-{HC[y]}{HR['iVario']}"; S[f"{HC[y]}{row}"].number_format = NUM
HR["iCombi"] = row; row += 2
header(S, row, "Ratios", {HC[y]: y for y in M.HIST})
row += 1
ratios = [("Sales growth", lambda c, p: f"={c}{HR['Sales revenues']}/{p}{HR['Sales revenues']}-1" if p else None),
          ("Gross margin", lambda c, p: f"={c}{HR['Gross profit']}/{c}{HR['Sales revenues']}"),
          ("EBIT margin", lambda c, p: f"={c}{HR['EBIT']}/{c}{HR['Sales revenues']}"),
          ("Effective tax rate", lambda c, p: f"=-{c}{HR['Income taxes']}/{c}{HR['EBT']}"),
          ("D&A / sales", lambda c, p: f"={c}{HR['D&A']}/{c}{HR['Sales revenues']}"),
          ("Capex / sales", lambda c, p: f"=-{c}{HR['Capex']}/{c}{HR['Sales revenues']}"),
          ("NWC (inventories + receivables − payables) / sales",
           lambda c, p: f"=({c}{HR['Inventories']}+{c}{HR['Trade receivables']}-{c}{HR['Trade payables']})/{c}{HR['Sales revenues']}"),
          ("iVario share of sales", lambda c, p: f"={c}{HR['iVario']}/{c}{HR['Sales revenues']}")]
for lab, fn in ratios:
    S.cell(row=row, column=1, value=lab)
    for i, y in enumerate(M.HIST):
        p = HC[M.HIST[i - 1]] if i > 0 else None
        f = fn(HC[y], p)
        if f:
            S[f"{HC[y]}{row}"] = f; S[f"{HC[y]}{row}"].number_format = PCT
    HR["ratio_" + lab] = row; row += 1

# ---------------------------------------------------------------------------------------------------------------------
# Revenue build (three scenario blocks)
R = sheet("Revenue build")
R["A1"] = "Revenue build: product group × region, 2026–2035 (EUR m)"; R["A1"].font = BOLD
R["A2"] = ("Rational does not disclose sales by product group within each region. The model assumes the group-wide iVario "
           "share applies in every region (an assumption, not reported data).")
RB = {}
row = 4
for s in SC:
    blk = {}
    sc = SCOL[s]
    header(R, row, f"{s} case", {YC[y]: y for y in M.YEARS})
    row += 1
    R.cell(row=row, column=1, value="Sales growth by region").font = Font(italic=True); row += 1
    for reg in M.REGIONS:
        R.cell(row=row, column=1, value=reg)
        gr = GROW[reg]
        for i, y in enumerate(M.YEARS):
            mid = f"(Inputs!$C${gr}+Inputs!${sc}${srow['Growth shift vs base, 2027–2030']})"
            if y == 2026:
                f = f"=Inputs!$B${gr}+Inputs!${sc}${srow['Growth shift vs base, 2026']}"
            elif y <= 2030:
                f = f"={mid}"
            else:
                f = f"={mid}+(Inputs!$D${gr}-{mid})*{y - 2030}/5"
            R[f"{YC[y]}{row}"] = f; R[f"{YC[y]}{row}"].number_format = PCT
        blk["g_" + reg] = row; row += 1
    R.cell(row=row, column=1, value="Sales by region").font = Font(italic=True); row += 1
    for reg in M.REGIONS:
        R.cell(row=row, column=1, value=reg)
        for i, y in enumerate(M.YEARS):
            prev = f"History!$L${HR['reg_' + reg]}" if y == 2026 else f"{YC[y - 1]}{row}"
            R[f"{YC[y]}{row}"] = f"={prev}*(1+{YC[y]}{blk['g_' + reg]})"; R[f"{YC[y]}{row}"].number_format = NUM
        blk["s_" + reg] = row; row += 1
    R.cell(row=row, column=1, value="Total sales").font = BOLD
    first, last = blk["s_" + M.REGIONS[0]], blk["s_" + M.REGIONS[-1]]
    for y in M.YEARS:
        R[f"{YC[y]}{row}"] = f"=SUM({YC[y]}{first}:{YC[y]}{last})"; R[f"{YC[y]}{row}"].number_format = NUM; R[f"{YC[y]}{row}"].font = BOLD
    blk["sales"] = row; row += 1
    R.cell(row=row, column=1, value="Growth")
    for y in M.YEARS:
        prev = f"History!$L${HR['Sales revenues']}" if y == 2026 else f"{YC[y - 1]}{blk['sales']}"
        R[f"{YC[y]}{row}"] = f"={YC[y]}{blk['sales']}/{prev}-1"; R[f"{YC[y]}{row}"].number_format = PCT
    blk["growth"] = row; row += 1
    R.cell(row=row, column=1, value="iVario share of sales (all regions)")
    for y in M.YEARS:
        prev = f"History!$L${HR['iVario']}/History!$L${HR['Sales revenues']}" if y == 2026 else f"{YC[y - 1]}{row}"
        step = f"Inputs!${sc}${srow['iVario share step per year, 2026–2030']}" if y <= 2030 else f"Inputs!${sc}${srow['iVario share step per year, 2031–2035']}"
        R[f"{YC[y]}{row}"] = f"={prev}+{step}"; R[f"{YC[y]}{row}"].number_format = PCT
    blk["ivs"] = row; row += 1
    for prod in ["iVario", "iCombi"]:
        R.cell(row=row, column=1, value=f"{prod} by region").font = Font(italic=True); row += 1
        for reg in M.REGIONS:
            R.cell(row=row, column=1, value=f"{prod} — {reg}")
            for y in M.YEARS:
                f = f"={YC[y]}{blk['s_' + reg]}*{YC[y]}{blk['ivs']}" if prod == "iVario" else f"={YC[y]}{blk['s_' + reg]}*(1-{YC[y]}{blk['ivs']})"
                R[f"{YC[y]}{row}"] = f; R[f"{YC[y]}{row}"].number_format = NUM
            blk[f"{prod}_{reg}"] = row; row += 1
        R.cell(row=row, column=1, value=f"{prod} total").font = BOLD
        for y in M.YEARS:
            R[f"{YC[y]}{row}"] = f"=SUM({YC[y]}{blk[prod + '_' + M.REGIONS[0]]}:{YC[y]}{blk[prod + '_' + M.REGIONS[-1]]})"
            R[f"{YC[y]}{row}"].number_format = NUM
        blk[prod] = row; row += 1
    RB[s] = blk
    row += 2

# ---------------------------------------------------------------------------------------------------------------------
# DCF (three scenario blocks)
Dd = sheet("DCF")
Dd["A1"] = "DCF: free cash flow to firm, 10-year explicit forecast, Gordon terminal value (EUR m)"; Dd["A1"].font = BOLD
DB = {}
row = 3
for s in SC:
    blk = {}
    sc, rb = SCOL[s], RB[s]
    header(Dd, row, f"{s} case", {YC[y]: y for y in M.YEARS})
    row += 1
    lines = [
        ("Sales", lambda y: f"='Revenue build'!{YC[y]}{rb['sales']}", NUM),
        ("EBIT margin", lambda y: f"=Inputs!${sc}${srow['EBIT margin 2026']}" if y == 2026 else (
            f"=Inputs!${sc}${srow['EBIT margin 2027']}" if y == 2027 else f"=Inputs!${sc}${srow['EBIT margin 2028–2035']}"), PCT),
        ("EBIT", lambda y: f"={YC[y]}{{Sales}}*{YC[y]}{{EBIT margin}}", NUM),
        ("Taxes on EBIT", lambda y: f"=-{YC[y]}{{EBIT}}*{REF['tax']}", NUM),
        ("NOPAT", lambda y: f"={YC[y]}{{EBIT}}+{YC[y]}{{Taxes on EBIT}}", NUM),
        ("D&A", lambda y: f"={YC[y]}{{Sales}}*{REF['da']}", NUM),
        ("Capex", lambda y: f"=-{YC[y]}{{Sales}}*{REF['capex1'] if y <= 2027 else REF['capex2']}", NUM),
        ("Change in NWC", lambda y: (f"=-({YC[y]}{{Sales}}-History!$L${HR['Sales revenues']})*{REF['nwc']}" if y == 2026
                                     else f"=-({YC[y]}{{Sales}}-{YC[y - 1]}{{Sales}})*{REF['nwc']}"), NUM),
        ("Lease payments", lambda y: f"=-{YC[y]}{{Sales}}*{REF['lease']}", NUM),
        ("FCFF", lambda y: f"={YC[y]}{{NOPAT}}+{YC[y]}{{D&A}}+{YC[y]}{{Capex}}+{YC[y]}{{Change in NWC}}+{YC[y]}{{Lease payments}}", NUM),
        ("FCFF counted (H2 only in 2026)", lambda y: f"={YC[y]}{{FCFF}}*{REF['h2']}" if y == 2026 else f"={YC[y]}{{FCFF}}", NUM),
        ("Discount period (years from publication)", lambda y: (f"=(DATE(2026,10,1)-{REF['date']})/365.25" if y == 2026
                                                               else f"=(DATE({y},7,1)-{REF['date']})/365.25"), NUM2),
        ("Discount factor", lambda y: f"=(1+{REF['ke']})^-{YC[y]}{{Discount period (years from publication)}}", "0.0000"),
        ("Present value", lambda y: f"={YC[y]}{{FCFF counted (H2 only in 2026)}}*{YC[y]}{{Discount factor}}", NUM),
    ]
    for lab, fn, fmt in lines:
        blk[lab] = row; row += 1
    for lab, fn, fmt in lines:
        rr = blk[lab]
        Dd.cell(row=rr, column=1, value=lab)
        for y in M.YEARS:
            f = fn(y)
            for k, v in blk.items():
                f = f.replace("{" + k + "}", str(v))
            Dd[f"{YC[y]}{rr}"] = f; Dd[f"{YC[y]}{rr}"].number_format = fmt
    Dd[f"A{blk['FCFF']}"].font = BOLD
    row += 1
    vals = [("Sum of PV, explicit period", f"=SUM(C{blk['Present value']}:L{blk['Present value']})", NUM),
            ("Terminal value at 31 Dec 2035", f"=L{blk['FCFF']}*(1+{REF['g']})/({REF['ke']}-{REF['g']})", NUM),
            ("PV of terminal value", f"=B{{Terminal value at 31 Dec 2035}}*(1+{REF['ke']})^-((DATE(2035,12,31)-{REF['date']})/365.25)", NUM),
            ("Enterprise value", "=B{Sum of PV, explicit period}+B{PV of terminal value}", NUM),
            ("Net cash (30 June 2026)", f"={REF['ncash']}", NUM),
            ("Equity value", "=B{Enterprise value}+B{Net cash (30 June 2026)}", NUM),
            ("Value per share today (EUR)", f"=B{{Equity value}}/{REF['shares']}", EUR),
            ("FY2026 dividend paid within 12 months (EUR)", f"={REF['payout']}*C{blk['NOPAT']}/{REF['shares']}", EUR),
            ("12-month target (EUR) = value × (1 + ke) − dividend", f"=B{{Value per share today (EUR)}}*(1+{REF['ke']})-B{{FY2026 dividend paid within 12 months (EUR)}}", EUR),
            ("Terminal value share of EV", "=B{PV of terminal value}/B{Enterprise value}", PCT)]
    for lab, f, fmt in vals:
        blk[lab] = row; row += 1
    for lab, f, fmt in vals:
        rr = blk[lab]
        for k, v in blk.items():
            f = f.replace("{" + k + "}", str(v))
        Dd.cell(row=rr, column=1, value=lab)
        Dd[f"B{rr}"] = f; Dd[f"B{rr}"].number_format = fmt
    Dd[f"A{blk['12-month target (EUR) = value × (1 + ke) − dividend']}"].font = BOLD
    DB[s] = blk
    row += 2

# ---------------------------------------------------------------------------------------------------------------------
# Scenarios summary
X = sheet("Scenarios")
X["A1"] = "Scenarios: bear / base / bull, weighted 25% / 50% / 25%"; X["A1"].font = BOLD
header(X, 3, "", {"B": "Bear", "C": "Base", "D": "Bull", "E": "Weighted"})
XS = {"Bear": "B", "Base": "C", "Bull": "D"}
summ = [("Weight", lambda s: f"=Inputs!{SCOL[s]}{WROW}", "0%"),
        ("Sales 2030 (EUR m)", lambda s: f"='Revenue build'!G{RB[s]['sales']}", NUM),
        ("Sales CAGR 2025–2035", lambda s: f"=('Revenue build'!L{RB[s]['sales']}/History!$L${HR['Sales revenues']})^(1/10)-1", PCT),
        ("EBIT margin 2028–2035", lambda s: f"=Inputs!{SCOL[s]}{srow['EBIT margin 2028–2035']}", PCT),
        ("Enterprise value (EUR m)", lambda s: f"=DCF!B{DB[s]['Enterprise value']}", NUM),
        ("Value per share today (EUR)", lambda s: f"=DCF!B{DB[s]['Value per share today (EUR)']}", EUR),
        ("12-month target (EUR)", lambda s: f"=DCF!B{DB[s]['12-month target (EUR) = value × (1 + ke) − dividend']}", EUR)]
for k, (lab, fn, fmt) in enumerate(summ):
    rr = 4 + k
    X.cell(row=rr, column=1, value=lab)
    for s in SC:
        X[f"{XS[s]}{rr}"] = fn(s); X[f"{XS[s]}{rr}"].number_format = fmt
    if lab not in ("Weight", "EBIT margin 2028–2035", "Sales CAGR 2025–2035"):
        X[f"E{rr}"] = f"=SUMPRODUCT($B$4:$D$4,B{rr}:D{rr})"; X[f"E{rr}"].number_format = fmt
TP_ROW = 4 + len(summ) - 1
X[f"A{TP_ROW + 2}"] = "Probability-weighted 12-month price target (EUR)"; X[f"A{TP_ROW + 2}"].font = BOLD
X[f"B{TP_ROW + 2}"] = f"=E{TP_ROW}"; X[f"B{TP_ROW + 2}"].number_format = EUR; X[f"B{TP_ROW + 2}"].font = BOLD
X[f"A{TP_ROW + 3}"] = "Share price (EUR)"; X[f"B{TP_ROW + 3}"] = f"={REF['price']}"; X[f"B{TP_ROW + 3}"].number_format = EUR
X[f"A{TP_ROW + 4}"] = "Upside / downside"; X[f"B{TP_ROW + 4}"] = f"=B{TP_ROW + 2}/B{TP_ROW + 3}-1"; X[f"B{TP_ROW + 4}"].number_format = PCT
X[f"A{TP_ROW + 5}"] = "Rating (Buy ≥ +15%, Sell ≤ −10%, else Hold)"; X[f"A{TP_ROW + 5}"].font = BOLD
X[f"B{TP_ROW + 5}"] = f'=IF(B{TP_ROW + 4}>=0.15,"Buy",IF(B{TP_ROW + 4}<=-0.1,"Sell","Hold"))'; X[f"B{TP_ROW + 5}"].font = BOLD
TPREF = f"Scenarios!$B${TP_ROW + 2}"

# ---------------------------------------------------------------------------------------------------------------------
# Sensitivity: weighted target across WACC (±1pp) and terminal growth (1–3%)
Z = sheet("Sensitivity")
Z["A1"] = "Probability-weighted 12-month target (EUR) by cost of equity and terminal growth"; Z["A1"].font = BOLD
Z["A2"] = "Each cell re-discounts the three scenarios' FCFF rows; centre = model inputs."
grows = [0.01, 0.015, 0.02, 0.025, 0.03]
shifts = [-0.01, -0.005, 0, 0.005, 0.01]
Z["A4"] = "Cost of equity ↓ / terminal growth →"; Z["A4"].font = BOLD
for j, g in enumerate(grows):
    c = Z.cell(row=4, column=2 + j, value=g); c.number_format = "0.0%"; c.font = BOLD; c.fill = HEAD
for i, d in enumerate(shifts):
    rr = 5 + i
    c = Z.cell(row=rr, column=1, value=f"={REF['ke']}+{d}"); c.number_format = "0.00%"; c.font = BOLD; c.fill = HEAD
    for j in range(len(grows)):
        w, g = f"$A{rr}", f"{L(2 + j)}$4"
        parts = []
        for s in SC:
            b = DB[s]
            fc, tr, fl = (f"DCF!$C${b['FCFF counted (H2 only in 2026)']}:$L${b['FCFF counted (H2 only in 2026)']}",
                          f"DCF!$C${b['Discount period (years from publication)']}:$L${b['Discount period (years from publication)']}",
                          f"DCF!$L${b['FCFF']}")
            ev = (f"SUMPRODUCT({fc},(1+{w})^(-{tr}))+{fl}*(1+{g})/({w}-{g})*(1+{w})^(-((DATE(2035,12,31)-{REF['date']})/365.25))")
            ps = f"(({ev})+{REF['ncash']})/{REF['shares']}*(1+{w})-DCF!$B${b['FY2026 dividend paid within 12 months (EUR)']}"
            parts.append(f"Inputs!${SCOL[s]}${WROW}*({ps})")
        c = Z.cell(row=rr, column=2 + j, value="=" + "+".join(parts)); c.number_format = "€#,##0"
Z["A11"] = "Upside vs share price"; Z["A11"].font = BOLD
for i in range(5):
    rr = 12 + i
    Z.cell(row=rr, column=1, value=f"=A{5 + i}").number_format = "0.00%"
    for j in range(5):
        Z.cell(row=rr, column=2 + j, value=f"={L(2 + j)}{5 + i}/{REF['price']}-1").number_format = "0%"

# ---------------------------------------------------------------------------------------------------------------------
# Comps
C = sheet("Comps")
C["A1"] = "Trading comparables: next-twelve-months EV/EBIT and P/E (consensus from MarketScreener, 7 Oct 2026)"; C["A1"].font = BOLD
CT, notes = comps_table()
cols = ["Price (local)", "Market cap (local m)", "Net debt (local m)", "EBIT FY1", "EBIT FY2", "EPS FY1", "EPS FY2", "NTM weight FY1"]
header(C, 3, "Company", {L(2 + k): c for k, c in enumerate(cols)} | {"J": "NTM EBIT", "K": "NTM EPS", "L": "EV/EBIT NTM", "M": "P/E NTM"})
for i, (name, rr_) in enumerate(CT.iterrows()):
    rr = 4 + i
    C.cell(row=rr, column=1, value=name)
    for k, c in enumerate(cols):
        cell = C.cell(row=rr, column=2 + k, value=float(rr_[c])); cell.number_format = "#,##0.00"; cell.font = BLUE; cell.fill = INPUT
    C[f"J{rr}"] = f"=I{rr}*E{rr}+(1-I{rr})*F{rr}"; C[f"K{rr}"] = f"=I{rr}*G{rr}+(1-I{rr})*H{rr}"
    C[f"L{rr}"] = f"=(C{rr}+D{rr})/J{rr}"; C[f"M{rr}"] = f"=B{rr}/K{rr}"
    for col in "JK":
        C[f"{col}{rr}"].number_format = "#,##0.00"
    for col in "LM":
        C[f"{col}{rr}"].number_format = '0.0"x"'
n = len(CT)
C[f"A{4 + n}"] = "Peer median (excl. Rational)"; C[f"A{4 + n}"].font = BOLD
C[f"L{4 + n}"] = f"=MEDIAN(L5:L{3 + n})"; C[f"M{4 + n}"] = f"=MEDIAN(M5:M{3 + n})"
C[f"L{4 + n}"].number_format = '0.0"x"'; C[f"M{4 + n}"].number_format = '0.0"x"'
C[f"A{5 + n}"] = "Rational premium to peer median"; C[f"L{5 + n}"] = f"=L4/L{4 + n}-1"; C[f"M{5 + n}"] = f"=M4/M{4 + n}-1"
C[f"L{5 + n}"].number_format = "0%"; C[f"M{5 + n}"].number_format = "0%"
for k, t in enumerate(notes):
    C.cell(row=8 + n + k, column=1, value=t).font = Font(italic=True, color="666666")
C.column_dimensions["A"].width = 30

# ---------------------------------------------------------------------------------------------------------------------
# ROIC vs cost of equity
O = sheet("ROIC")
O["A1"] = "Return on invested capital vs. cost of capital, 2016–2025"; O["A1"].font = BOLD
O["A2"] = ("ROIC = EBIT × (1 − effective tax rate) / average invested capital; invested capital = equity + pensions − cash "
           "− other current financial assets (deposits). Cost of capital = year-end 10-year Bund + Blume beta × Damodaran "
           "implied ERP at the start of the next year.")
header(O, 4, "", {HC[y]: y for y in M.HIST})
roic = M.roic_history()
labels = [("Invested capital (EUR m)", "ic"), ("NOPAT (EUR m)", "nopat"), ("ROIC", "roic"), ("10-year Bund, year-end", "rf"),
          ("Implied ERP (Damodaran, January following)", "erp"), ("Cost of capital", "ke")]
for k, (lab, key) in enumerate(labels):
    rr = 5 + k
    O.cell(row=rr, column=1, value=lab)
    for y in M.HIST:
        v = roic.loc[y, key]
        if key == "ic":
            c = O[f"{HC[y]}{rr}"]; c.value = (f"=History!{HC[y]}{HR['Equity']}+History!{HC[y]}{HR['Pensions']}-History!{HC[y]}{HR['Cash']}"
                                              f"-N(History!{HC[y]}{HR['Other current financial assets']})-N(History!{HC[y]}{HR['Fixed deposits > 3 months']})"); c.number_format = NUM
        elif key == "nopat":
            O[f"{HC[y]}{rr}"] = f"=History!{HC[y]}{HR['EBIT']}*(1+History!{HC[y]}{HR['Income taxes']}/History!{HC[y]}{HR['EBT']})"
            O[f"{HC[y]}{rr}"].number_format = NUM
        elif key == "roic":
            prev = f"{HC[y - 1]}5" if y > 2016 else f"{HC[y]}5"
            O[f"{HC[y]}{rr}"] = f"={HC[y]}6/AVERAGE({prev},{HC[y]}5)"; O[f"{HC[y]}{rr}"].number_format = PCT
        elif key in ("rf", "erp"):
            c = O[f"{HC[y]}{rr}"]; c.value = round(float(v), 5); c.number_format = "0.00%"; c.font = BLUE
        else:
            O[f"{HC[y]}{rr}"] = f"={HC[y]}8+{REF['beta']}*{HC[y]}9"; O[f"{HC[y]}{rr}"].number_format = PCT
ch = LineChart(); ch.title = "ROIC vs cost of capital"; ch.height, ch.width = 7, 16
ch.add_data(Reference(O, min_col=2, max_col=12, min_row=7), titles_from_data=False, from_rows=True)
ch.add_data(Reference(O, min_col=2, max_col=12, min_row=10), titles_from_data=False, from_rows=True)
ch.set_categories(Reference(O, min_col=3, max_col=12, min_row=4))
O.add_chart(ch, "A13")

# ---------------------------------------------------------------------------------------------------------------------
# Cover
V = wb["Sheet"]; V.title = "Cover"
V.column_dimensions["A"].width = 48; V.column_dimensions["B"].width = 18
V["A1"] = "Rational AG (Xetra: RAA) — valuation model"; V["A1"].font = Font(bold=True, size=14)
V["A2"] = "Investment Research Portfolio · Project 1 · publication date 7 October 2026"
cov = [("Share price (EUR)", f"={REF['price']}", EUR), ("Probability-weighted 12-month target (EUR)", f"={TPREF}", EUR),
       ("Upside / downside", f"=Scenarios!B{TP_ROW + 4}", PCT), ("Rating", f"=Scenarios!B{TP_ROW + 5}", None),
       ("Cost of equity (= WACC)", f"={REF['ke']}", "0.00%"), ("Terminal growth", f"={REF['g']}", "0.0%")]
for k, (lab, f, fmt) in enumerate(cov):
    V.cell(row=4 + k, column=1, value=lab).font = BOLD
    c = V.cell(row=4 + k, column=2, value=f)
    if fmt:
        c.number_format = fmt
V["A12"] = "Sheets: Inputs → History → Revenue build → DCF → Scenarios → Sensitivity; Comps and ROIC are cross-checks."
wb.move_sheet("Cover", offset=-wb.index(wb["Cover"]))
OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)
print("wrote", OUT)
