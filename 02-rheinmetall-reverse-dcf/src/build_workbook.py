"""Writes model/rheinmetall_reverse_dcf.xlsx. Every valuation number is an Excel formula. The two reverse-DCF inputs
(implied CAGR and implied margin) hold the values src/model.py solves for; in Excel, Goal Seek on the 'difference to
price' cell reproduces them (Data > What-If Analysis > Goal Seek). src/check_workbook.py recalculates the workbook in
LibreOffice and confirms both differences are zero and the case values match the Python model.

    python src/build_workbook.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT)]
import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter as L

from src import model as M
from src import nato as N
from src import peers as PE

OUT = ROOT / "model" / "rheinmetall_reverse_dcf.xlsx"
R = M.run()
mk = R["mk"]
BLUE, BOLD = Font(color="1F4E79"), Font(bold=True)
INPUT = PatternFill("solid", fgColor="FFF4D6")
HEAD = PatternFill("solid", fgColor="E8ECF2")
HIGHLIGHT = PatternFill("solid", fgColor="F8CBAD")
YC = {y: L(3 + i) for i, y in enumerate(M.YEARS)}      # 2026..2035 in C..L
wb = Workbook()


def sh(name, wa=48):
    ws = wb.create_sheet(name)
    ws.column_dimensions["A"].width = wa
    for c in range(2, 30):
        ws.column_dimensions[L(c)].width = 12
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


# ---------------------------------------------------------------------------------------------------------------------
I = sh("Inputs")
I["A1"] = "Rheinmetall reverse DCF — inputs (blue on yellow = input; everything else is a formula)"; I["A1"].font = BOLD
rows = [
    ("Valuation date", M.PUB.to_pydatetime(), "yyyy-mm-dd", None),
    ("Share price, 7 Oct 2026 (EUR, Xetra close, yfinance)", mk["price"], "#,##0.00", None),
    ("Shares outstanding (m): 46,777,223 issued − 121,504 treasury", mk["shares_m"], "0.000", None),
    ("10-year Bund yield (Bundesbank, 7 Oct 2026)", mk["rf"], "0.00%", None),
    ("Implied ERP (Damodaran, Oct 2026)", mk["erp"], "0.00%", None),
    ("Raw beta vs STOXX Europe 600 (60 monthly returns to Sep 2026)", mk["beta_raw"], "0.000", None),
    ("Blume-adjusted beta", "=0.67*B9+0.33", "0.000", None),
    ("Cost of equity", "=B7+B10*B8", "0.00%", None),
    ("Bond XS3344481935 price (Börse Frankfurt, 7 Oct 2026)", mk["bond_price"], "0.00", None),
    ("Bond yield to maturity (Excel YIELD, settlement 9 Oct 2026)", "=YIELD(DATE(2026,10,9),DATE(2031,5,28),0.03375,B12,100,1,1)", "0.00%", None),
    ("Tax rate (2023–2025 average effective, continuing operations)", mk["tax"], "0.00%", None),
    ("Market value of equity (EUR m)", "=B5*B6", "#,##0", None),
    ("Debt: financial debts + pensions, 30 Jun 2026 (EUR m)", M.GROSS_DEBT, "#,##0", None),
    ("WACC", "=B15/(B15+B16)*B11+B16/(B15+B16)*B13*(1-B14)", "0.00%", None),
    ("Terminal growth", M.G_TERM, "0.0%", None),
    ("Sales 2025, continuing operations (EUR m)", M.SALES_2025, "#,##0", None),
    ("Operating margin 2025", M.MARGIN_2025, "0.0%", None),
    ("Sales-to-incremental-capital ratio k (calibrated, see note)", R["k"], "0.00", None),
    ("Management: sales 2026 (guidance midpoint, EUR m)", M.MGMT["sales_2026"], "#,##0", None),
    ("Management: sales 2030 (EUR m)", M.MGMT["sales_2030"], "#,##0", None),
    ("Management: operating margin 2030", M.MGMT["margin_2030"], "0.0%", None),
]
for i, (lab, v, fmt, _) in enumerate(rows):
    r = 4 + i
    I[f"A{r}"] = lab
    if isinstance(v, str) and v.startswith("="):
        put(I, f"B{r}", v, fmt)
    else:
        inp(I, f"B{r}", v, fmt)
REF = {k: f"Inputs!$B${4 + i}" for i, k in enumerate(["date", "price", "shares", "rf", "erp", "beta_raw", "beta", "ke", "bondpx", "kd", "tax",
                                                      "E", "D", "wacc", "g", "s25", "m25", "k", "s26", "s30", "m30"])}
I["A26"] = ("k is set so that management's own plan (2026 guidance, EUR 50bn and 20% in 2030) converts 50% of 2026–2030 operating "
            "result into free cash flow, its cash-conversion target (src/model.py calibrate_k).")
I["A28"] = "Bridge from enterprise value to equity value (30 June 2026, H1 2026 report)"; I["A28"].font = BOLD
for j, (lab, v) in enumerate(M.BRIDGE.items()):
    I[f"A{29 + j}"] = lab; inp(I, f"B{29 + j}", v, "#,##0")
I[f"A{29 + len(M.BRIDGE)}"] = "Total adjustment"; put(I, f"B{29 + len(M.BRIDGE)}", f"=SUM(B29:B{28 + len(M.BRIDGE)})", "#,##0", True)
REF["bridge"] = f"Inputs!$B${29 + len(M.BRIDGE)}"
I.column_dimensions["A"].width = 64

# ---------------------------------------------------------------------------------------------------------------------
H = sh("History", 40)
Hd = M.history()
H["A1"] = "Rheinmetall key figures (AR 2025 multi-year table; continuing operations as restated there), EUR m"; H["A1"].font = BOLD
for j, y in enumerate(Hd.columns):
    put(H, f"{L(2 + j)}3", int(y), None, True)
for i, (lab, row) in enumerate(Hd.iterrows()):
    H[f"A{4 + i}"] = lab
    for j, y in enumerate(Hd.columns):
        if pd.notna(row[y]):
            inp(H, f"{L(2 + j)}{4 + i}", float(row[y]), "#,##0.0")
r0 = 4 + len(Hd)
H[f"A{r0}"] = "Operating margin"
H[f"A{r0 + 1}"] = "Book-to-bill (Rheinmetall Nomination / sales)"
for j, y in enumerate(Hd.columns):
    c = L(2 + j)
    put(H, f"{c}{r0}", f"={c}{4 + list(Hd.index).index('Operating result')}/{c}{4 + list(Hd.index).index('Sales')}", "0.0%")
    if pd.notna(Hd.loc["Rheinmetall Nomination", y]):
        put(H, f"{c}{r0 + 1}", f"={c}{4 + list(Hd.index).index('Rheinmetall Nomination')}/{c}{4 + list(Hd.index).index('Sales')}", "0.00")

# ---------------------------------------------------------------------------------------------------------------------
B = sh("Budget", 22)
B["A1"] = ("European NATO members' equipment spending to 2035 (USD m): NATO 2025e level, share of GDP on a straight line to 3.5% "
           "in 2035 (members above 3.5% stay at their 2025e share), IMF WEO nominal GDP; equipment share held at 2025e")
t2, t3, t8 = N.tables()
gdp = N.imf_gdp()
hdr = ["Country", "Core defence 2025e (USD m)", "Share of GDP 2025e (%)", "Equipment share 2025e (%)"] + [f"GDP {y} (USD bn)" for y in range(2025, 2036)] \
      + [f"Equipment {y}" for y in range(2025, 2036)]
for j, h in enumerate(hdr):
    c = B.cell(row=3, column=1 + j, value=h); c.font = BOLD; c.fill = HEAD
for i, c in enumerate(N.EUROPE):
    r = 4 + i
    B[f"A{r}"] = c
    inp(B, f"B{r}", float(t2.loc[c, "2025e"]), "#,##0")
    inp(B, f"C{r}", float(t3.loc[c, "2025e"]), "0.00")
    inp(B, f"D{r}", float(t8.loc[c, "2025e"]), "0.00")
    for k, y in enumerate(range(2025, 2036)):
        inp(B, f"{L(5 + k)}{r}", float(gdp.loc[c, y]), "#,##0.0")
        g0, gy = f"$E{r}", f"{L(5 + k)}{r}"
        share = f"MAX($C{r}/100,$C{r}/100+(3.5%-$C{r}/100)*({y}-2025)/10)"
        B.cell(row=r, column=16 + k, value=f"=$B{r}*$D{r}/100*({share})/($C{r}/100)*{gy}/{g0}").number_format = "#,##0"
last = 3 + len(N.EUROPE)
B[f"A{last + 1}"] = "Total (USD m)"; B[f"A{last + 1}"].font = BOLD
for k in range(11):
    col = L(16 + k)
    put(B, f"{col}{last + 1}", f"=SUM({col}4:{col}{last})", "#,##0", True)
B[f"A{last + 2}"] = "EUR/USD (7 Oct 2026, yfinance)"; inp(B, f"B{last + 2}", R["fx"], "0.0000")
B[f"A{last + 3}"] = "Total (EUR m)"; B[f"A{last + 3}"].font = BOLD
B[f"A{last + 4}"] = "Growth"
for k in range(11):
    col = L(16 + k)
    put(B, f"{col}{last + 3}", f"={col}{last + 1}/$B${last + 2}", "#,##0", True)
    if k:
        put(B, f"{col}{last + 4}", f"={col}{last + 3}/{L(15 + k)}{last + 3}-1", "0.0%")
BUD = {y: f"Budget!${L(16 + (y - 2025))}${last + 3}" for y in range(2025, 2036)}
BUDG = {y: f"Budget!${L(16 + (y - 2025))}${last + 4}" for y in range(2026, 2036)}
B[f"A{last + 6}"] = "Rheinmetall's European sales share 2025 (Germany 3,774 + other Europe 4,264) / 9,935"
inp(B, f"B{last + 6}", M.EUR_SALES_SHARE_2025, "0.0%")
REF["eushare"] = f"Budget!$B${last + 6}"
B.freeze_panes = "B4"


# ---------------------------------------------------------------------------------------------------------------------
def dcf_block(ws, top, title, sales_f, margin_f):
    """Writes a DCF block; sales_f(y, col) / margin_f(y, col) return formulas. Returns the row of value per share."""
    ws[f"A{top}"] = title; ws[f"A{top}"].font = BOLD
    for y in M.YEARS:
        put(ws, f"{YC[y]}{top}", y, None, True)
    lab = ["Sales", "Operating margin", "EBIT", "NOPAT", "Reinvestment (Δsales / k)", "FCFF", "FCFF counted (H2 only in 2026)",
           "Years from valuation date", "Present value"]
    rr = {l: top + 1 + i for i, l in enumerate(lab)}
    for l, r in rr.items():
        ws[f"A{r}"] = l
    for y in M.YEARS:
        c = YC[y]; prev = REF["s25"] if y == 2026 else f"{YC[y - 1]}{rr['Sales']}"
        put(ws, f"{c}{rr['Sales']}", sales_f(y, c), "#,##0")
        put(ws, f"{c}{rr['Operating margin']}", margin_f(y, c), "0.0%")
        put(ws, f"{c}{rr['EBIT']}", f"={c}{rr['Sales']}*{c}{rr['Operating margin']}", "#,##0")
        put(ws, f"{c}{rr['NOPAT']}", f"={c}{rr['EBIT']}*(1-{REF['tax']})", "#,##0")
        put(ws, f"{c}{rr['Reinvestment (Δsales / k)']}", f"=-({c}{rr['Sales']}-{prev})/{REF['k']}", "#,##0")
        put(ws, f"{c}{rr['FCFF']}", f"={c}{rr['NOPAT']}+{c}{rr['Reinvestment (Δsales / k)']}", "#,##0")
        put(ws, f"{c}{rr['FCFF counted (H2 only in 2026)']}", f"={c}{rr['FCFF']}*{0.5 if y == 2026 else 1}", "#,##0")
        d = "DATE(2026,10,1)" if y == 2026 else f"DATE({y},7,1)"
        put(ws, f"{c}{rr['Years from valuation date']}", f"=({d}-{REF['date']})/365.25", "0.00")
        put(ws, f"{c}{rr['Present value']}", f"={c}{rr['FCFF counted (H2 only in 2026)']}*(1+{REF['wacc']})^-{c}{rr['Years from valuation date']}", "#,##0")
    b = top + 11
    items = [("PV of FCFF", f"=SUM(C{rr['Present value']}:L{rr['Present value']})"),
             ("Terminal FCFF 2036", f"=L{rr['Sales']}*(1+{REF['g']})*L{rr['Operating margin']}*(1-{REF['tax']})-L{rr['Sales']}*{REF['g']}/{REF['k']}"),
             ("PV of terminal value", f"=B{b + 1}/({REF['wacc']}-{REF['g']})*(1+{REF['wacc']})^-((DATE(2035,12,31)-{REF['date']})/365.25)"),
             ("Enterprise value", f"=B{b}+B{b + 2}"), ("Equity value", f"=B{b + 3}+{REF['bridge']}"),
             ("Value per share (EUR)", f"=B{b + 4}/{REF['shares']}"), ("Difference to share price", f"=B{b + 5}-{REF['price']}")]
    for i, (l, f) in enumerate(items):
        ws[f"A{b + i}"] = l; put(ws, f"B{b + i}", f, "#,##0.00", l.startswith(("Value", "Difference")))
    return b + 5


Rv = sh("Reverse DCF")
Rv["A1"] = "Reverse DCF: what the share price implies"; Rv["A1"].font = BOLD
Rv["A3"] = "(a) Implied 2025–2035 sales CAGR at management's 20% target margin"; Rv["A3"].font = BOLD
Rv["A4"] = "Implied CAGR (Goal Seek: set the difference cell below to 0 by changing this cell)"
inp(Rv, "B4", R["a_cagr"], "0.00%")
ps_a = dcf_block(Rv, 6, "Block (a)", lambda y, c: f"={REF['s25']}*(1+$B$4)^({y}-2025)",
                 lambda y, c: f"={REF['m25']}+({REF['m30']}-{REF['m25']})*MIN({y}-2025,5)/5")
Rv[f"A{ps_a + 3}"] = "(b) Implied steady-state operating margin at management's sales path (EUR 50bn in 2030, then budget growth)"
Rv[f"A{ps_a + 3}"].font = BOLD
Rv[f"A{ps_a + 4}"] = "Implied margin from 2030 (Goal Seek: set the difference cell below to 0 by changing this cell)"
inp(Rv, f"B{ps_a + 4}", R["b_margin"], "0.00%")
mcell = f"$B${ps_a + 4}"


def mgmt_sales(y, c, target=f"{REF['s30']}"):
    if y == 2026:
        return f"={REF['s26']}"
    if y <= 2030:
        return f"={YC[y - 1]}{{row}}*({target}/{REF['s26']})^(1/4)"
    return f"={YC[y - 1]}{{row}}*(1+{BUDG[y]})"


def fill_row(fn, row):
    return lambda y, c: fn(y, c).replace("{row}", str(row))


top_b = ps_a + 6
ps_b = dcf_block(Rv, top_b, "Block (b)", fill_row(mgmt_sales, top_b + 1),
                 lambda y, c: f"={REF['m25']}+({mcell}-{REF['m25']})*MIN({y}-2025,5)/5")

# ---------------------------------------------------------------------------------------------------------------------
Cs = sh("Cases")
Cs["A1"] = "Our cases: 2026 at guidance midpoint, constant growth to the 2030 sales level, then European equipment-budget growth"
Cs["A1"].font = BOLD
CASES = {"Bear": (30000.0, 0.15), "Base": (40000.0, 0.185), "Bull": (M.MGMT["sales_2030"], 0.21)}
case_rows, case_cells = {}, {}
top = 3
for n, (s30, m30) in CASES.items():
    Cs[f"A{top}"] = f"{n}: 2030 sales (EUR m)"; inp(Cs, f"B{top}", s30, "#,##0")
    Cs[f"A{top + 1}"] = f"{n}: operating margin from 2030"; inp(Cs, f"B{top + 1}", m30, "0.0%")
    s30c, m30c = f"$B${top}", f"$B${top + 1}"
    t = top + 3
    psr = dcf_block(Cs, t, f"{n} case", fill_row(lambda y, c, s=s30c: mgmt_sales(y, c, s), t + 1),
                    lambda y, c, m=m30c: f"={REF['m25']}+({m}-{REF['m25']})*MIN({y}-2025,5)/5")
    case_rows[n] = psr; case_cells[n] = {"sales_row": t + 1, "margin_row": t + 2}
    top = psr + 4

# ---------------------------------------------------------------------------------------------------------------------
G = sh("Grid", 30)
G["A1"] = "Value per share (EUR) by 2025–2035 sales CAGR (rows) and operating margin from 2030 (columns); shaded = within 10% of the share price"
G["A1"].font = BOLD
cagrs = [round(0.05 + 0.025 * i, 3) for i in range(9)]
margins = [round(0.10 + 0.01 * j, 2) for j in range(11)]
for j, m in enumerate(margins):
    c = G.cell(row=3, column=2 + j, value=m); c.number_format = "0%"; c.font = BOLD; c.fill = HEAD
for i, cg in enumerate(cagrs):
    r = 4 + i
    c = G.cell(row=r, column=1, value=cg); c.number_format = "0.0%"; c.font = BOLD; c.fill = HEAD
    for j in range(len(margins)):
        cr, mr = f"$A{r}", f"{L(2 + j)}$3"
        S = lambda y: f"{REF['s25']}*(1+{cr})^{y - 2025}"
        Mg = lambda y: f"({REF['m25']}+({mr}-{REF['m25']})*{min(y - 2025, 5)}/5)"
        terms = []
        for y in M.YEARS:
            prev = REF["s25"] if y == 2026 else S(y - 1)
            fc = f"({S(y)}*{Mg(y)}*(1-{REF['tax']})-({S(y)}-{prev})/{REF['k']})"
            d = "DATE(2026,10,1)" if y == 2026 else f"DATE({y},7,1)"
            terms.append(f"{fc}*{0.5 if y == 2026 else 1}*(1+{REF['wacc']})^-(({d}-{REF['date']})/365.25)")
        tv = (f"({S(2035)}*(1+{REF['g']})*{Mg(2035)}*(1-{REF['tax']})-{S(2035)}*{REF['g']}/{REF['k']})/({REF['wacc']}-{REF['g']})"
              f"*(1+{REF['wacc']})^-((DATE(2035,12,31)-{REF['date']})/365.25)")
        G.cell(row=r, column=2 + j, value=f"=({'+'.join(terms)}+{tv}+{REF['bridge']})/{REF['shares']}").number_format = "#,##0"
rng = f"B4:{L(1 + len(margins))}{3 + len(cagrs)}"
G.conditional_formatting.add(rng, FormulaRule(formula=[f"ABS(B4/{REF['price']}-1)<=0.1"], fill=HIGHLIGHT))
G[f"A{5 + len(cagrs)}"] = "Share price"; put(G, f"B{5 + len(cagrs)}", f"={REF['price']}", "#,##0.00")

# ---------------------------------------------------------------------------------------------------------------------
P = sh("Peers", 26)
pm = PE.margins()
P["A1"] = "EBIT margin (MarketScreener, 7 Oct 2026; 2026–2028 = consensus)"; P["A1"].font = BOLD
for j, y in enumerate(pm.columns):
    put(P, f"{L(2 + j)}3", int(y), None, True)
put(P, "J3", "5-yr avg 2021–25", None, True); put(P, "K3", "Best 2021–25", None, True)
for i, (co, row) in enumerate(pm.iterrows()):
    r = 4 + i
    P[f"A{r}"] = co
    for j, y in enumerate(pm.columns):
        inp(P, f"{L(2 + j)}{r}", float(row[y]), "0.0%")
    put(P, f"J{r}", f"=AVERAGE(B{r}:F{r})", "0.0%"); put(P, f"K{r}", f"=MAX(B{r}:F{r})", "0.0%")
peer_rows = [4 + i for i, co in enumerate(pm.index) if co != "Rheinmetall"]
P[f"A{5 + len(pm)}"] = "Peers (excl. Rheinmetall): best 5-yr average"; put(P, f"J{5 + len(pm)}", "=MAX(" + ",".join(f"J{r}" for r in peer_rows) + ")", "0.0%")
P[f"A{6 + len(pm)}"] = "Peers (excl. Rheinmetall): best single year"; put(P, f"K{6 + len(pm)}", "=MAX(" + ",".join(f"K{r}" for r in peer_rows) + ")", "0.0%")

# ---------------------------------------------------------------------------------------------------------------------
T = sh("Tests", 60)
T["A1"] = "Three tests of what the price implies, against our base and bull cases"; T["A1"].font = BOLD
for j, h in enumerate(["Implied by price", "Bear", "Base", "Bull", "Above bull?", "Between base and bull?"]):
    put(T, f"{L(2 + j)}3", h, None, True)
cs = {n: f"Cases!" for n in CASES}
# budget test: share of European equipment spending in 2035
T["A4"] = "Budget: Rheinmetall European sales 2035 / European NATO equipment spending 2035"
put(T, "B4", f"='Reverse DCF'!L7*{REF['eushare']}/{BUD[2035]}", "0.0%")
for j, n in enumerate(CASES):
    put(T, f"{L(3 + j)}4", f"=Cases!L{case_cells[n]['sales_row']}*{REF['eushare']}/{BUD[2035]}", "0.0%")
T["A5"] = "  memo: Rheinmetall's share today (2025 European sales / 2025 equipment spending)"
put(T, "B5", f"={REF['s25']}*{REF['eushare']}/{BUD[2025]}", "0.0%")
T["A6"] = "Backlog: cumulative sales 2026–2030 (EUR m) vs Rheinmetall Backlog EUR 80.5bn (30 Jun 2026)"
put(T, "B6", "=SUM('Reverse DCF'!C7:G7)", "#,##0")
for j, n in enumerate(CASES):
    put(T, f"{L(3 + j)}6", f"=SUM(Cases!C{case_cells[n]['sales_row']}:G{case_cells[n]['sales_row']})", "#,##0")
T["A7"] = "Margin: operating margin from 2030"
put(T, "B7", f"={mcell.replace('$', '')}".replace("=B", "='Reverse DCF'!B"), "0.0%")
for j, n in enumerate(CASES):
    put(T, f"{L(3 + j)}7", f"=Cases!L{case_cells[n]['margin_row']}", "0.0%")
for r in (4, 6, 7):
    put(T, f"F{r}", f'=IF(B{r}>E{r},"yes","no")'); put(T, f"G{r}", f'=IF(AND(B{r}>D{r},B{r}<=E{r}),"yes","no")')
T["A9"] = "Recommendation rule"; T["A9"].font = BOLD
put(T, "B9", '=IF(COUNTIF(F4:F7,"yes")>=2,"Sell (short)",IF(COUNTIF(G4:G7,"yes")>=2,"Hold: priced for perfection",'
             'IF(AND(B4<D4,B6<D6,B7<D7),"Buy","Hold")))', None, True)
T["A11"] = "Case values per share (EUR)"; T["A11"].font = BOLD
for j, n in enumerate(CASES):
    put(T, f"{L(3 + j)}11", f"=Cases!B{case_rows[n]}", "#,##0")

# ---------------------------------------------------------------------------------------------------------------------
V = wb["Sheet"]; V.title = "Cover"
V.column_dimensions["A"].width = 60; V.column_dimensions["B"].width = 18
V["A1"] = "Rheinmetall AG (RHM GY) — reverse DCF, 7 October 2026"; V["A1"].font = Font(bold=True, size=14)
cov = [("Share price (EUR)", f"={REF['price']}", "#,##0.00"), ("WACC", f"={REF['wacc']}", "0.00%"),
       ("(a) Implied 2025–2035 sales CAGR at 20% margin", "='Reverse DCF'!B4", "0.0%"),
       ("    → implied 2035 sales (EUR m)", "='Reverse DCF'!L7", "#,##0"),
       ("(b) Implied margin at management's sales path", f"='Reverse DCF'!B{ps_a + 4}", "0.0%"),
       ("Recommendation", "=Tests!B9", None)]
for i, (l, f, fmt) in enumerate(cov):
    V[f"A{3 + i}"] = l; put(V, f"B{3 + i}", f, fmt, True)
V["A10"] = "Sheets: Inputs → History → Budget → Reverse DCF (a, b) → Cases → Grid → Peers → Tests"
OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)
print("wrote", OUT, "| value-per-share rows:", ps_a, ps_b, case_rows)
