"""Lager model/kvartalsrapport_mal.xlsx fra tallene i data/ (Pareto Eiendomsfellesskap, Q1–Q3 2026).

Malen er laget for gjenbruk: legg inn et nytt kvartal som en ny kolonne i arket «Input», oppdater «Eiendommer»,
«Utløpsprofil», «Historikk» og «Kontantstrømmer», og velg kvartalet i Input!B2. Alle nøkkeltall i arket «Nøkkeltall»
er formler. src/lag_rapport.py leser arbeidsboken og lager investorrapporten.

    python src/lag_mal.py
"""
from pathlib import Path

import re

import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
OUT = ROOT / "model" / "kvartalsrapport_mal.xlsx"
BLUE, BOLD = Font(color="1F4E79"), Font(bold=True)
INPUT = PatternFill("solid", fgColor="FFF4D6")
HEAD = PatternFill("solid", fgColor="E8ECF2")
WRAP = Alignment(wrap_text=True, vertical="top")
N_Q = 12                                  # plass til 12 kvartaler i Input (C..N)

K = pd.read_csv(D / "kvartalstall_PEF.csv", index_col=0, dtype=str)
E = pd.read_csv(D / "eiendommer_PEF_Q3_2026.csv")
H = pd.read_csv(D / "kvartalsavkastning_PEF.csv")
CF = pd.read_csv(D / "kontantstrommer_PEF_2026.csv")
U = pd.read_csv(D / "utlopsprofil_PEF_Q3_2026.csv")

wb = Workbook()


def sheet(name, wa=44, w=14):
    ws = wb.create_sheet(name)
    ws.column_dimensions["A"].width = wa
    for c in range(2, 30):
        ws.column_dimensions[L(c)].width = w
    return ws


def header(ws, row, labels, col=1):
    for j, h in enumerate(labels):
        c = ws.cell(row=row, column=col + j, value=h)
        c.font = BOLD; c.fill = HEAD; c.alignment = WRAP


def inp(cell, v, fmt=None):
    cell.value = v; cell.font = BLUE; cell.fill = INPUT
    if fmt:
        cell.number_format = fmt


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return v if isinstance(v, str) and v == v else None


# --- Les meg -----------------------------------------------------------------------------------------------------------
R = wb.active; R.title = "Les meg"; R.column_dimensions["A"].width = 110
lines = [
    ("Kvartalsrapport – gjenbrukbar mal", True),
    ("Eksempeldata: Pareto Eiendomsfellesskap IS/AS (PEF), kvartalsrapporter Q1–Q3 2026 (paretoai.no/reports).", False),
    ("", False),
    ("Slik oppdaterer du for et nytt kvartal", True),
    ("1. Input: fyll inn neste ledige kolonne (gule celler) med tallene fra kvartalsrapporten. Kvartalsnavnet står i rad 4.", False),
    ("2. Input!B2: velg kvartalet rapporten skal gjelde (nedtrekksliste).", False),
    ("3. Historikk: legg til en rad med kvartalets avkastning og utbetaling (% av innbetalt kapital).", False),
    ("4. Eiendommer og Utløpsprofil: lim inn porteføljelisten og utløpsprofilen fra rapporten.", False),
    ("5. Kontantstrømmer: legg til kvartalets innkallinger (negativt fortegn) og utbetalinger (positivt) med dato, og VEK ved periodeslutt.", False),
    ("6. Nøkkeltall og Kontroller oppdateres automatisk. Kjør deretter `python src/lag_rapport.py` for PDF-rapporten.", False),
    ("", False),
    ("Fargekoder: blå tekst på gul bakgrunn = input; svart = formel. Beløp i NOK mill. der ikke annet er angitt.", False),
]
for i, (t, b) in enumerate(lines):
    R.cell(row=1 + i, column=1, value=t).font = Font(bold=b, size=13 if i == 0 else 11)

# --- Input -------------------------------------------------------------------------------------------------------------
I = sheet("Input", 46, 13)
I["A1"] = "Nøkkeltall per kvartal (fra kvartalsrapportene)"; I["A1"].font = BOLD
I["A2"] = "Valgt kvartal for rapporten"; I["A2"].font = BOLD
inp(I["B2"], K.columns[-1])
I["A4"] = "Nøkkeltall"; I["A4"].font = BOLD; I["A4"].fill = HEAD
for j in range(N_Q):
    c = I.cell(row=4, column=3 + j, value=K.columns[j] if j < len(K.columns) else None)
    c.font = BOLD; c.fill = HEAD
    if j >= len(K.columns):
        c.fill = INPUT
I["B4"] = "Enhet"; I["B4"].font = BOLD; I["B4"].fill = HEAD
UNIT = {"Dato": "dato", "Utbyttedato": "dato"}
ROWS = {}
for i, lab in enumerate(K.index):
    r = 5 + i
    ROWS[lab] = r
    I.cell(row=r, column=1, value=lab)
    I.cell(row=r, column=2, value=UNIT.get(lab, "%" if "(%)" in lab else ("år" if "(år)" in lab else ("kvm" if "kvm" in lab else ("antall" if "Antall" in lab else "NOK mill.")))))
    for j, q in enumerate(K.columns):
        v = K.loc[lab, q]
        cell = I.cell(row=r, column=3 + j)
        if lab in UNIT and isinstance(v, str):
            inp(cell, pd.Timestamp(v).to_pydatetime(), "yyyy-mm-dd")
        else:
            x = num(v)
            inp(cell, x / 100 if (x is not None and "(%)" in lab) else x, "0.0%" if "(%)" in lab else "#,##0.0")
    for j in range(len(K.columns), N_Q):
        I.cell(row=r, column=3 + j).fill = INPUT
QRANGE = f"Input!$C$4:${L(2 + N_Q)}$4"
dv = DataValidation(type="list", formula1=f"=$C$4:${L(2 + N_Q)}$4", allow_blank=False)
I.add_data_validation(dv); dv.add("B2")
I.freeze_panes = "C5"


def sel(lab, offset=0):
    """Verdien for nøkkeltallet i valgt kvartal (offset −1 = forrige kvartal)."""
    r = ROWS[lab]
    return f"INDEX(Input!$C${r}:${L(2 + N_Q)}${r},MATCH(Input!$B$2,{QRANGE},0){'+' + str(offset) if offset > 0 else str(offset) if offset < 0 else ''})"


# --- Historikk ---------------------------------------------------------------------------------------------------------
Hs = sheet("Historikk", 10, 16)
Hs["A1"] = "Kvartalsavkastning og utbetaling (% av innbetalt kapital), kjedet IRR-metode (Q3 2026-rapporten s. 6)"; Hs["A1"].font = BOLD
header(Hs, 3, ["År", "Kvartal", "Kvartalsnavn", "Løpenummer", "Avkastning", "Utbetaling i % av innbetalt kapital", "Kjedet indeks"])
for i, r_ in H.reset_index(drop=True).iterrows():
    rr = 4 + i
    inp(Hs.cell(row=rr, column=1), int(r_["År"])); inp(Hs.cell(row=rr, column=2), r_["Kvartal"])
    Hs.cell(row=rr, column=3, value=f'=B{rr}&" "&A{rr}')
    Hs.cell(row=rr, column=4, value=i + 1 if i == 0 else f"=D{rr - 1}+1")
    inp(Hs.cell(row=rr, column=5), None if pd.isna(r_["Avkastning (%)"]) else r_["Avkastning (%)"] / 100, "0.0%")
    v = r_["Utbetaling i % av innbetalt kapital"]
    inp(Hs.cell(row=rr, column=6), None if pd.isna(v) else v / 100, "0.0%")
    Hs.cell(row=rr, column=7, value=f"=(1+E{rr})" if i == 0 else f"=G{rr - 1}*(1+N(E{rr}))").number_format = "0.000"
HLAST = 4 + len(H) + 40                 # plass til 40 nye kvartaler
Hs.freeze_panes = "A4"
HR = lambda col: f"Historikk!${col}$4:${col}${HLAST}"

# --- Kontantstrømmer ---------------------------------------------------------------------------------------------------
C = sheet("Kontantstrømmer", 14, 16)
C["A1"] = "Daterte kontantstrømmer for investorene samlet (NOK mill.). Fortegn: innbetaling/VEK ved start = negativ, utbetaling/VEK ved slutt = positiv."
C["A1"].font = BOLD
header(C, 3, ["Dato", "Type", "Beløp", "Kilde / forutsetning"])
C.column_dimensions["B"].width = 26; C.column_dimensions["D"].width = 90
for i, r_ in CF.iterrows():
    rr = 4 + i
    inp(C.cell(row=rr, column=1), pd.Timestamp(r_["Dato"]).to_pydatetime(), "yyyy-mm-dd")
    inp(C.cell(row=rr, column=2), r_["Type"]); inp(C.cell(row=rr, column=3), float(r_["Beløp"]), "#,##0.0")
    C.cell(row=rr, column=4, value=r_["Kilde"]).alignment = WRAP
CLAST = 4 + len(CF) + 40

# --- Eiendommer og utløpsprofil ------------------------------------------------------------------------------------
Es = sheet("Eiendommer", 26, 20)
header(Es, 1, list(E.columns))
Es.column_dimensions["E"].width = 46
for i, r_ in E.iterrows():
    for j, c in enumerate(E.columns):
        inp(Es.cell(row=2 + i, column=1 + j), r_[c], "#,##0" if c == "Areal (kvm)" else None)
ELAST = 2 + len(E) + 60
Us = sheet("Utløpsprofil", 14, 22)
header(Us, 1, ["År", "Andel av leieinntekter"])
for i, r_ in U.iterrows():
    inp(Us.cell(row=2 + i, column=1), int(r_["År"])); inp(Us.cell(row=2 + i, column=2), r_["Andel (%)"] / 100, "0.0%")
ULAST = 2 + len(U) + 20

# --- Nøkkeltall --------------------------------------------------------------------------------------------------------
N = sheet("Nøkkeltall", 58, 16)
N["A1"] = "Nøkkeltall for valgt kvartal (alle celler er formler)"; N["A1"].font = BOLD
N["A2"] = "Kvartal"; N["B2"] = "=Input!B2"; N["B2"].font = BOLD
N["A3"] = "Løpenummer i Historikk"
N["B3"] = f"=MATCH(Input!B2,{HR('C')},0)"
idx = f"{HR('D')}"
rows = [
    ("Porteføljestatus", None, None),
    ("Rapportdato", f"={sel('Dato')}", "yyyy-mm-dd"),
    ("Antall bygg", f"={sel('Antall bygg')}", "0"),
    ("Antall leietakere", f"={sel('Antall leietakere')}", "0"),
    ("Areal (kvm)", f"={sel('Areal (kvm)')}", "#,##0"),
    ("Areal i eiendomslisten (kvm)", f"=SUM(Eiendommer!F2:F{ELAST})", "#,##0"),
    ("Brutto eiendomsverdi (NOK mill.)", f"={sel('Brutto eiendomsverdi')}", "#,##0"),
    ("Eiendomsverdi per kvm (NOK)", "=«Brutto eiendomsverdi (NOK mill.)»/«Areal (kvm)»*1000000", "#,##0"),
    ("Vektet gjenværende leietid (år)", f"={sel('Vektet gjenværende leietid (år)')}", "0.0"),
    ("Leieinntekter", None, None),
    ("Brutto annualiserte leieinntekter (NOK mill.)", f"={sel('Brutto annualiserte leieinntekter')}", "#,##0"),
    ("Endring fra forrige kvartal (NOK mill.)", f"=IFERROR(«Brutto annualiserte leieinntekter (NOK mill.)»-{sel('Brutto annualiserte leieinntekter', -1)},\"\")", "#,##0"),
    ("Leie per kvm (NOK)", "=«Brutto annualiserte leieinntekter (NOK mill.)»/«Areal (kvm)»*1000000", "#,##0"),
    ("Andel KPI-regulert", f"={sel('KPI-regulering (%)')}", "0%"),
    ("Utleiegrad", None, None),
    ("Økonomisk ledighet", f"={sel('Økonomisk ledighet (%)')}", "0.0%"),
    ("Økonomisk utleiegrad (1 − ledighet)", "=1-«Økonomisk ledighet»", "0.0%"),
    ("Arealmessig utleiegrad (eiendomslisten)", f"=1-SUMIF(Eiendommer!E2:E{ELAST},\"Ledig areal\",Eiendommer!F2:F{ELAST})/«Areal i eiendomslisten (kvm)»", "0.0%"),
    ("Avkastning", None, None),
    ("Kvartalets avkastning", f"=INDEX({HR('E')},$B$3)", "0.0%"),
    ("Hittil i år (kjedet)", f"=EXP(SUMPRODUCT(({HR('A')}=INDEX({HR('A')},$B$3))*({idx}<=$B$3)*LN(1+{HR('E')})))-1", "0.0%"),
    ("Siste 12 måneder (fire kvartaler kjedet)", f"=EXP(SUMPRODUCT(({idx}>$B$3-4)*({idx}<=$B$3)*LN(1+{HR('E')})))-1", "0.0%"),
    ("Aggregert siden oppstart (kjedet)", f"=EXP(SUMPRODUCT(({idx}<=B3)*LN(1+{HR('E')})))-1", "0.0%"),
    ("Annualisert siden oppstart (kjedet)", f"=(1+«Aggregert siden oppstart (kjedet)»)^(4/COUNT(INDEX({HR('E')},1):INDEX({HR('E')},$B$3)))-1", "0.00%"),
    ("IRR siden oppstart, rapportert av forvalter", f"={sel('IRR siden oppstart, rapportert (%)')}", "0.0%"),
    ("IRR for perioden i Kontantstrømmer (XIRR)", f"=XIRR(Kontantstrømmer!C4:C{4 + len(CF) - 1},Kontantstrømmer!A4:A{4 + len(CF) - 1})", "0.00%"),
    ("Samme, omregnet til perioden", f"=(1+«IRR for perioden i Kontantstrømmer (XIRR)»)^((MAX(Kontantstrømmer!A4:A{CLAST})-MIN(Kontantstrømmer!A4:A{CLAST}))/365)-1", "0.00%"),
    ("Direkteavkastning", None, None),
    ("Utbetaling siste fire kvartaler (% av innbetalt kapital)", f"=SUMPRODUCT(({idx}>$B$3-4)*({idx}<=$B$3)*{HR('F')})", "0.0%"),
    ("Annualisert utbytte (4 × kvartalets) i % av VEK", f"=4*{sel('Utbytte i kvartalet')}/{sel('VEK')}", "0.0%"),
    ("Netto yield (eiendomsnivå)", f"={sel('Netto yield (%)')}", "0.0%"),
    ("Netto yield justert for ledighet", f"={sel('Netto yield justert for ledighet (%)')}", "0.0%"),
    ("Brutto leieinntekt / eiendomsverdi", "=«Brutto annualiserte leieinntekter (NOK mill.)»/«Brutto eiendomsverdi (NOK mill.)»", "0.0%"),
    ("Multipler", None, None),
    ("Innkalt kapital (NOK mill.)", f"={sel('Innkalt kapital')}", "#,##0"),
    ("Akkumulerte utbetalinger (NOK mill.)", f"={sel('Akkumulerte utbetalinger')}", "#,##0"),
    ("Verdijustert egenkapital, VEK (NOK mill.)", f"={sel('VEK')}", "#,##0"),
    ("DPI (utbetalt / innkalt)", "=«Akkumulerte utbetalinger (NOK mill.)»/«Innkalt kapital (NOK mill.)»", "0.00x"),
    ("RVPI (VEK / innkalt)", "=«Verdijustert egenkapital, VEK (NOK mill.)»/«Innkalt kapital (NOK mill.)»", "0.00x"),
    ("TVPI (utbetalt + VEK) / innkalt", "=«DPI (utbetalt / innkalt)»+«RVPI (VEK / innkalt)»", "0.00x"),
    ("Utbetalt i % av innkalt kapital", "=«DPI (utbetalt / innkalt)»", "0.0%"),
    ("Uinnkalt kapital (NOK mill.)", f"={sel('Bestilt (uinnkalt) kapital')}", "#,##0"),
]
NR = {}
r = 5
for lab, f, fmt in rows:
    NR[lab] = r
    r += 1
TOK = re.compile(r"«([^»]+)»")
for lab, f, fmt in rows:
    r = NR[lab]
    N.cell(row=r, column=1, value=lab)
    if f is None:
        N.cell(row=r, column=1).font = BOLD; N.cell(row=r, column=1).fill = HEAD
        continue
    c = N.cell(row=r, column=2, value=TOK.sub(lambda m: f"B{NR[m.group(1)]}", f)); c.number_format = fmt
NB = lambda lab: f"Nøkkeltall!$B${NR[lab]}"

# --- Kontroller ---------------------------------------------------------------------------------------------------
Ks = sheet("Kontroller", 66, 16)
Ks["A1"] = "Avstemming av kvartalsrapporten (avvik over toleranse markeres rødt)"; Ks["A1"].font = BOLD
header(Ks, 3, ["Kontroll", "Beregnet", "Rapportert", "Avvik", "Toleranse"])
checks = [
    ("Aggregert avkastning: kjedet kvartalstall vs rapportert", "="+NB("Aggregert siden oppstart (kjedet)"), f"={sel('Aggregert avkastning siden oppstart (%)')}", 0.01, "0.0%"),
    ("Areal: sum eiendomsliste vs rapportert totalareal (kvm)", "="+NB("Areal i eiendomslisten (kvm)"), "="+NB("Areal (kvm)"), 5, "#,##0"),
    ("Utbetalinger: endring i akkumulert vs utbytte i kvartalet", f"=IFERROR({sel('Akkumulerte utbetalinger')}-{sel('Akkumulerte utbetalinger', -1)},\"\")",
     f"={sel('Utbytte i kvartalet')}", 3, "#,##0.0"),
    ("Utløpsprofil: sum andeler + økonomisk ledighet", f"=SUM(Utløpsprofil!B2:B{ULAST})+"+NB("Økonomisk ledighet"), "=1", 0.02, "0.0%"),
    ("Kvartalets avkastning: Historikk vs Input", "="+NB("Kvartalets avkastning"), f"={sel('Kvartalets avkastning (%)')}", 0.0005, "0.0%"),
    ("VEK-bro: VEK start + innkalt − utbytte + verdiendring = VEK slutt (implisitt avkastning)",
     f"=IFERROR(({sel('VEK')}-{sel('VEK', -1)}-({sel('Innkalt kapital')}-{sel('Innkalt kapital', -1)})+{sel('Utbytte i kvartalet')})/{sel('VEK', -1)},\"\")",
     f"={sel('Kvartalets avkastning (%)')}", 0.003, "0.00%"),
]
for i, (lab, a, b, tol, fmt) in enumerate(checks):
    r = 4 + i
    Ks.cell(row=r, column=1, value=lab).alignment = WRAP
    Ks.cell(row=r, column=2, value=a).number_format = fmt
    Ks.cell(row=r, column=3, value=b).number_format = fmt
    Ks.cell(row=r, column=4, value=f'=IFERROR(B{r}-C{r},"")').number_format = fmt
    inp(Ks.cell(row=r, column=5), tol, fmt)
red = PatternFill("solid", fgColor="F8CBAD")
Ks.conditional_formatting.add(f"D4:D{3 + len(checks)}", CellIsRule(operator="notBetween", formula=[f"-E4", "E4"], fill=red))

OUT.parent.mkdir(exist_ok=True)
wb.save(OUT)
print("skrev", OUT)
