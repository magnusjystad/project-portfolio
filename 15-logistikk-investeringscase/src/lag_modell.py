"""Lager model/fugleasen7_investeringscase.xlsx: kontantstrøm, yield, IRR (ufinansiert og belånt), maks bud og
sensitivitet på markedsleie × exit-yield, pluss marked, sammenlignbare transaksjoner og leietakeranalyse.
Inndata er blå på gul bakgrunn; alt annet er formler. src/sjekk_modell.py kontrollerer mot src/modell.py.

    python src/lag_modell.py
"""
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as L

import modell as Mo

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
OUT = ROOT / "model" / "fugleasen7_investeringscase.xlsx"
MD = pd.read_csv(D / "markedsdata.csv").set_index("Nøkkel")
A = Mo.ANTAGELSER
BLUE, BOLD = Font(color="1F4E79"), Font(bold=True)
INPUT = PatternFill("solid", fgColor="FFF4D6")
HEAD = PatternFill("solid", fgColor="E8ECF2")
WRAP = Alignment(wrap_text=True, vertical="top")
PCT, MILL, KR = "0.00%", "#,##0.0", "#,##0"
wb = Workbook()


def inp(c, v, fmt=None):
    c.value = v; c.font = BLUE; c.fill = INPUT
    if fmt:
        c.number_format = fmt


def head(ws, row, labels, col=1):
    for j, h in enumerate(labels):
        c = ws.cell(row=row, column=col + j, value=h)
        c.font = BOLD; c.fill = HEAD; c.alignment = WRAP


# --- Les meg -------------------------------------------------------------------------------------------------------------
LM = wb.active; LM.title = "Les meg"; LM.column_dimensions["A"].width = 120
for i, t in enumerate([
    "Investeringscase: Fugleåsen 7, Langhus (Nordre Follo). 21 012 m² lager/logistikk, leietaker Norsk Lastbærer Pool AS (NLP).",
    "",
    "Slik er modellen bygd:",
    "• Forutsetninger: markedsdata med kilde (blå på gul) og antagelser (blå på gul, merket «antagelse»). Endre bare disse cellene.",
    "• Kontantstrøm: årlig leie, eierkostnader, utleiekostnader og netto driftsinntekt 2027–2037; kjøp 31.12.2026, salg 31.12.2036 på 2037-NOI.",
    "  NLP-kontrakten løper til utløpsdatoen; deretter står bygget tomt i valgt antall måneder før ny leie til markedsleie.",
    "  Leien reguleres årlig med KPI for året før (Norges Banks anslag, PPR 3/2026; 2 % fra 2030).",
    "• Avkastning: IRR, multippel, netto startyield, pris per m² og maks bud ved avkastningskravet; belånt IRR med avdragsfritt lån.",
    "• Sensitivitet: IRR ved budet og maks bud for markedsleie (rader) × exit-yield (kolonner). Beregnes i arket Scenarier.",
    "  NOI er lineær i markedsleien (kontraktsdel + markedsleie × koeffisient, se Kontantstrøm rad 16–18), så hvert scenario er én rad.",
    "• Marked: sammenlignbare transaksjoner (pris per m² og brutto yield er formler) og markedsleie per område.",
    "• Leietaker: NLPs regnskap 2023–2025 (Regnskapsregisteret) med nøkkeltall for motpartsrisiko.",
    "• Kontroller: summer som skal være null.",
    "",
    "Holdetiden er låst til 10 år av oppsettet. Kjøpesummen er satt til budet (formel), men kan overskrives med et tall.",
    "Antagelser er ikke observerte tall. De er begrunnet i README og memoet.",
]):
    LM[f"A{i + 1}"] = t
LM["A1"].font = Font(bold=True, size=13)

# --- Forutsetninger -----------------------------------------------------------------------------------------------------
F = wb.create_sheet("Forutsetninger")
for col, w in zip("ABCDE", (52, 14, 16, 70, 24)):
    F.column_dimensions[col].width = w
F["A1"] = "Forutsetninger (blå på gul = inndata)"; F["A1"].font = BOLD
head(F, 3, ["Markedsdata og fakta", "Verdi", "Enhet", "Kilde", "Status"])
REF, r = {}, 4
fmt = {"andel": "0.00%", "år": "0.00", "m2": KR, "NOK mill.": "0.000", "NOK/m2/år": KR}
for k, row in MD.iterrows():
    F[f"A{r}"] = row["Beskrivelse"]; inp(F[f"B{r}"], float(row["Verdi"]), fmt.get(row["Enhet"], "0.000"))
    F[f"C{r}"] = row["Enhet"]; F[f"D{r}"] = row["Kilde"]; F[f"E{r}"] = row["Status"]
    for c in "ADE":
        F[f"{c}{r}"].alignment = WRAP
    REF[k] = f"Forutsetninger!$B${r}"; r += 1
r += 1
head(F, r, ["Antagelser (ikke observerte tall)", "Verdi", "Enhet", "Begrunnelse", ""]); r += 1
ant = [("kjop_aar", "Kjøpsår (oppgjør 31.12.)", A["kjop_aar"], "år", "0", "Oppgjør ved årsskiftet 2026/27"),
       ("kpi_andel", "Andel av KPI som reguleres inn i leien", A["kpi_andel"], "andel", "0%", "Finanstilsynet: leien justeres vanligvis årlig med KPI"),
       ("markedsleie", "Markedsleie ved reutleie, 2026-kroner", A["markedsleie"], "NOK/m2/år", KR, "Midt i Akershus Eiendoms intervall for Langhus (1 400–1 700)"),
       ("ledighet_mnd", "Ledighet etter utløp", A["ledighet_mnd"], "måneder", "0", "Tid til ny leietaker; ledigheten i Stor-Oslo er 4,3 %"),
       ("utleiekost", "Utleiekostnad (megler, tilpasning), andel av første års leie", A["utleiekost"], "andel", "0%", "Antagelse"),
       ("eierkost", "Eierkostnader, andel av brutto leie", A["eierkost"], "andel", "0%", "Skatteetatens sjablong 10 %"),
       ("exit_yield", "Exit-yield (netto)", A["exit_yield"], "andel", PCT, "Netto yield i PEFs siste verdivurdering (5,8 %)"),
       ("kjopskost", "Kjøpskostnader, andel av kjøpesum", A["kjopskost"], "andel", PCT, "Selskapskjøp, ingen dokumentavgift"),
       ("salgskost", "Salgskostnader, andel av salgsverdi", A["salgskost"], "andel", PCT, "Antagelse"),
       ("krav", "Avkastningskrav, ufinansiert IRR", A["krav"], "andel", PCT, "Prime yield 5,5 % + KPI-mål 2 %; 10-års stat 4,4 % + 3 % risikopremie"),
       ("ltv", "Belåningsgrad (LTV)", A["ltv"], "andel", "0%", "Antagelse; avdragsfritt"),
       ("rente", "Lånerente", A["rente"], "andel", PCT, "Newsec: snittrente næringseiendom ca. 6,2 % høsten 2026")]
for k, lab, v, enh, f_, beg in ant:
    F[f"A{r}"] = lab; inp(F[f"B{r}"], v, f_); F[f"C{r}"] = enh; F[f"D{r}"] = beg; F[f"D{r}"].alignment = WRAP
    REF[k] = f"Forutsetninger!$B${r}"; r += 1
r += 1
head(F, r, ["Avledet", "Verdi", "Enhet", "Formel", ""]); r += 1
avl = [("leie26", "Kontraktsleie 2026 (100 %)", f"={REF['leie_2025']}*(1+{REF['kpi_andel']}*{REF['kpi_nov_2025']})", "NOK mill.", "0.000", "Leie 2025 × (1 + KPI nov. 2025)"),
       ("leie26_m2", "Kontraktsleie 2026 per m²", f"={{leie26}}*1000000/{REF['areal']}", "NOK/m2/år", KR, ""),
       ("utlop", "Utløp NLP-kontrakt (desimalår)", f"={REF['leieavtale_start']}+{REF['leieavtale_lengde']}", "år", "0.00", "2033,75 = 30.9.2033"),
       ("ny_start", "Ny leie starter (desimalår)", f"={{utlop}}+{REF['ledighet_mnd']}/12", "år", "0.00", ""),
       ("reversjon", "Markedsleie / dagens leie − 1", f"={REF['markedsleie']}/{{leie26_m2}}-1", "andel", "0%", "")]
for k, lab, fx, enh, f_, beg in avl:
    F[f"A{r}"] = lab; F[f"B{r}"] = fx.format(**{kk: REF[kk] for kk in REF}); F[f"B{r}"].number_format = f_
    F[f"C{r}"] = enh; F[f"D{r}"] = beg; REF[k] = f"Forutsetninger!$B${r}"; r += 1
BUD_ROW = r + 1
F[f"A{BUD_ROW}"] = "Maks bud ved nedre markedsleie (1 400 kr/m²) og basis exit-yield (NOK mill.)"
F[f"A{BUD_ROW + 1}"] = "Bud: avrundet ned til nærmeste 5 mill."
F[f"A{BUD_ROW + 2}"] = "Kjøpesum (NOK mill.); standard = budet, kan overskrives"
REF["maks_lav"], REF["bud"], REF["pris"] = (f"Forutsetninger!$B${BUD_ROW + i}" for i in range(3))
r = BUD_ROW + 4
head(F, r, ["KPI-bane (for indeksering)", "KPI", "", "Kilde", ""]); r += 1
KPI0 = r
for y in range(2025, 2038):
    F[f"A{r}"] = y
    if y <= 2029:
        F[f"B{r}"] = f"={REF['kpi_nov_2025' if y == 2025 else f'kpi_{y}']}"
    else:
        F[f"B{r}"] = f"={REF['kpi_lang']}"
    F[f"B{r}"].number_format = "0.0%"; F[f"D{r}"] = "2025: november; 2026–2029: Norges Bank PPR 3/2026; deretter 2 %"; r += 1
KYR, KVAL = f"Forutsetninger!$A${KPI0}:$A${r - 1}", f"Forutsetninger!$B${KPI0}:$B${r - 1}"

# --- Kontantstrøm -------------------------------------------------------------------------------------------------------
K = wb.create_sheet("Kontantstrøm")
K.column_dimensions["A"].width = 50
for c in range(2, 15):
    K.column_dimensions[L(c)].width = 11
K["A1"] = "Kontantstrøm, NOK mill. (kolonne B = kjøpstidspunkt 31.12.2026; M = 2037, bare for exit-verdien)"; K["A1"].font = BOLD
COLS = [L(c) for c in range(2, 14)]           # B..M
YC = COLS[1:]                                  # C..M = 2027..2037
HOLD = YC[:-1]                                 # C..L = 2027..2036
lab = {4: "År", 5: "KPI brukt (året før) × andel", 6: "Indeks (2026 = 1)", 7: "Andel av året med NLP-kontrakt",
       8: "Andel av året med ny leietaker", 9: "Kontraktsleie, fullt år", 10: "Markedsleie for hele bygget, fullt år",
       11: "Brutto leieinntekt", 12: "Eierkostnader", 13: "Utleiekostnader", 14: "Netto driftsinntekt (NOI)",
       16: "NOI-bidrag fra NLP-kontrakten", 17: "NOI per kr/m² markedsleie", 18: "Kontroll: 16 + markedsleie × 17 − 14",
       19: "NOI ved nedre markedsleie (1 400 kr/m²)",
       21: "Kjøp inkl. kostnader", 22: "Netto driftsinntekt", 23: "Salgsverdi etter kostnader", 24: "Netto kontantstrøm, ufinansiert",
       26: "Lån (inn ved kjøp, ut ved salg)", 27: "Renter", 28: "Netto kontantstrøm, egenkapital"}
for rr, t in lab.items():
    K[f"A{rr}"] = t
for rr in (4, 14, 24, 28):
    K[f"A{rr}"].font = BOLD
K["B4"] = f"={REF['kjop_aar']}"; K["B6"] = 1
for i, c in enumerate(YC):
    p = COLS[i]
    K[f"{c}4"] = f"={p}4+1"
    K[f"{c}5"] = f"={REF['kpi_andel']}*INDEX({KVAL},MATCH({c}4-1,{KYR},0))"
    K[f"{c}6"] = f"={p}6*(1+{c}5)"
    K[f"{c}7"] = f"=MAX(0,MIN(1,{REF['utlop']}-{c}4))"
    K[f"{c}8"] = f"=MAX(0,MIN(1,{c}4+1-{REF['ny_start']}))"
    K[f"{c}9"] = f"={REF['leie26']}*{c}6"
    K[f"{c}10"] = f"={REF['markedsleie']}*{REF['areal']}*{c}6/1000000"
    K[f"{c}11"] = f"={c}7*{c}9+{c}8*{c}10"
    K[f"{c}12"] = f"={REF['eierkost']}*({c}7*{c}9+(1-{c}7)*{c}10)"
    flag = f"AND({REF['ny_start']}>={c}4,{REF['ny_start']}<{c}4+1)"
    K[f"{c}13"] = f"=IF({flag},{REF['utleiekost']}*{c}10,0)"
    K[f"{c}14"] = f"={c}11-{c}12-{c}13"
    K[f"{c}16"] = f"={c}7*{c}9*(1-{REF['eierkost']})"
    K[f"{c}17"] = f"={REF['areal']}*{c}6/1000000*({c}8-{REF['eierkost']}*(1-{c}7)-IF({flag},{REF['utleiekost']},0))"
    K[f"{c}18"] = f"={c}16+{REF['markedsleie']}*{c}17-{c}14"
    K[f"{c}19"] = f"={c}16+{REF['markedsleie_langhus_lav']}*{c}17"
for c in COLS:
    K[f"{c}4"].font = BOLD
    for rr in range(5, 9):
        K[f"{c}{rr}"].number_format = "0.000"
    for rr in list(range(9, 15)) + [16, 17, 18, 19] + list(range(21, 29)):
        K[f"{c}{rr}"].number_format = "#,##0.000" if rr == 17 else MILL
K["B21"] = f"=-{REF['pris']}*(1+{REF['kjopskost']})"
for c in HOLD:
    K[f"{c}22"] = f"={c}14"
K[f"{HOLD[-1]}23"] = f"=M14/{REF['exit_yield']}*(1-{REF['salgskost']})"
K["B24"] = "=B21"
for c in HOLD:
    K[f"{c}24"] = f"=SUM({c}22:{c}23)"
K["B26"] = f"={REF['ltv']}*{REF['pris']}"
for c in HOLD:
    K[f"{c}27"] = f"=-$B$26*{REF['rente']}"
K[f"{HOLD[-1]}26"] = "=-$B$26"
K["B28"] = "=B24+B26"
for c in HOLD:
    K[f"{c}28"] = f"={c}24+{c}26+{c}27"
F[f"B{BUD_ROW}"] = (f"=NPV({REF['krav']},Kontantstrøm!C19:K19,Kontantstrøm!L19+Kontantstrøm!M19/{REF['exit_yield']}*(1-{REF['salgskost']}))"
                    f"/(1+{REF['kjopskost']})")
F[f"B{BUD_ROW + 1}"] = f"=FLOOR({REF['maks_lav']},5)"
inp(F[f"B{BUD_ROW + 2}"], f"={REF['bud']}")
for i in range(3):
    F[f"B{BUD_ROW + i}"].number_format = MILL
for i in range(2):
    F[f"B{BUD_ROW + i}"].font = BOLD

# Nøkkeltall
NK = {}
nk = [("irr", "IRR, ufinansiert", "=IRR(B24:L24)", PCT),
      ("mult", "Multippel, ufinansiert", "=SUM(C24:L24)/-B24", "0.00x"),
      ("irr_bel", "IRR, egenkapital (belånt)", "=IRR(B28:L28)", PCT),
      ("mult_bel", "Multippel, egenkapital", "=SUM(C28:L28)/-B28", "0.00x"),
      ("startyield", "Netto startyield (NOI 2027 / kjøpesum)", f"=C14/{REF['pris']}", PCT),
      ("brutto_yield", "Brutto startyield (leie 2027 / kjøpesum)", f"=C11/{REF['pris']}", PCT),
      ("pris_m2", "Kjøpesum per m² (NOK)", f"={REF['pris']}*1000000/{REF['areal']}", KR),
      ("exit", "Salgsverdi 2036 etter kostnader", "=L23", MILL),
      ("exit_m2", "Salgsverdi per m² (NOK)", f"=L23*1000000/{REF['areal']}", KR),
      ("maks", "Maks bud ved avkastningskravet, basis", f"=NPV({REF['krav']},C24:L24)/(1+{REF['kjopskost']})", MILL),
      ("icr", "Rentedekning år 1 (NOI / renter)", "=C14/-C27", "0.00x")]
K["A31"] = "Nøkkeltall"; K["A31"].font = BOLD
for i, (k, t, fx, f_) in enumerate(nk):
    rr = 32 + i
    K[f"A{rr}"] = t; K[f"B{rr}"] = fx; K[f"B{rr}"].number_format = f_; K[f"B{rr}"].font = BOLD
    NK[k] = f"Kontantstrøm!$B${rr}"

# --- Scenarier (rad per markedsleie × exit-yield) ----------------------------------------------------------------------
S = wb.create_sheet("Scenarier")
S["A1"] = ("Én rad per kombinasjon. NOI(år) = kontraktsdel + markedsleie × koeffisient (Kontantstrøm rad 16–17); "
           "salgsverdi = NOI 2037 / exit-yield × (1 − salgskost).")
head(S, 3, ["Markedsleie (kr/m²)", "Exit-yield"] + [f"t{t}" for t in range(11)] + ["IRR ved kjøpesum", "Maks bud ved krav"])
S.column_dimensions["A"].width = 14
SROW = {}
rr = 4
for ml in Mo.LEIEGRID:
    for ey in Mo.YIELDGRID:
        inp(S[f"A{rr}"], ml, KR); inp(S[f"B{rr}"], ey, PCT)
        S[f"C{rr}"] = f"=-{REF['pris']}*(1+{REF['kjopskost']})"
        for t, c in enumerate(HOLD, start=1):
            col = L(3 + t)
            fx = f"=Kontantstrøm!{c}16+$A{rr}*Kontantstrøm!{c}17"
            if t == len(HOLD):
                fx += f"+(Kontantstrøm!M16+$A{rr}*Kontantstrøm!M17)/$B{rr}*(1-{REF['salgskost']})"
            S[f"{col}{rr}"] = fx; S[f"{col}{rr}"].number_format = MILL
        S[f"C{rr}"].number_format = MILL
        S[f"N{rr}"] = f"=IRR(C{rr}:M{rr})"; S[f"N{rr}"].number_format = PCT
        S[f"O{rr}"] = f"=NPV({REF['krav']},D{rr}:M{rr})/(1+{REF['kjopskost']})"; S[f"O{rr}"].number_format = MILL
        SROW[(ml, ey)] = rr; rr += 1

# Andel av verdien fra reutleie over dagens leie: maks bud om reutleien skjer til dagens leie per m²
lm = REF["leie26_m2"]
ledd = [f"{c}16+{lm}*{c}17" for c in HOLD]
ledd[-1] += f"+(M16+{lm}*M17)/{REF['exit_yield']}*(1-{REF['salgskost']})"
K["A44"] = "Maks bud om reutleien skjer til dagens leie per m²"
K["B44"] = f"=NPV({REF['krav']},{','.join(ledd)})/(1+{REF['kjopskost']})"
K["A45"] = "Andel av maks bud som skyldes reutleie over dagens leie"
K["B45"] = f"=1-B44/{NK['maks'].split('!')[1]}"
K["B44"].number_format = MILL; K["B45"].number_format = "0%"
for c in ("B44", "B45"):
    K[c].font = BOLD
NK["maks_dagens"], NK["andel_rev"] = "Kontantstrøm!$B$44", "Kontantstrøm!$B$45"

# --- Sensitivitet ----------------------------------------------------------------------------------------------------------
SE = wb.create_sheet("Sensitivitet")
SE.column_dimensions["A"].width = 26
SE["A1"] = "IRR (ufinansiert) ved kjøpesummen: markedsleie ved reutleie (rader, 2026-kr/m²) × exit-yield (kolonner)"; SE["A1"].font = BOLD
SE["A2"] = "Kjøpesum (NOK mill.)"; SE["B2"] = f"={REF['pris']}"; SE["B2"].number_format = MILL
nY = len(Mo.YIELDGRID)


def grid(top, col_letter, fmt_):
    SE[f"A{top}"] = "Markedsleie \\ exit-yield"; SE[f"A{top}"].font = BOLD
    for j, ey in enumerate(Mo.YIELDGRID):
        c = SE.cell(row=top, column=2 + j, value=ey); c.number_format = PCT; c.font = BOLD; c.fill = HEAD
    for i, ml in enumerate(Mo.LEIEGRID):
        c = SE.cell(row=top + 1 + i, column=1, value=ml); c.number_format = KR; c.font = BOLD; c.fill = HEAD
        for j, ey in enumerate(Mo.YIELDGRID):
            cc = SE.cell(row=top + 1 + i, column=2 + j, value=f"=Scenarier!{col_letter}{SROW[(ml, ey)]}"); cc.number_format = fmt_
    rng = f"B{top + 1}:{L(1 + nY)}{top + len(Mo.LEIEGRID)}"
    SE.conditional_formatting.add(rng, ColorScaleRule(start_type="min", start_color="F8696B", mid_type="percentile", mid_value=50,
                                                      mid_color="FFEB84", end_type="max", end_color="63BE7B"))


grid(4, "N", PCT)
T2 = 6 + len(Mo.LEIEGRID)
SE[f"A{T2 - 1}"] = "Maks bud (NOK mill.) ved avkastningskravet: markedsleie × exit-yield"; SE[f"A{T2 - 1}"].font = BOLD
grid(T2, "O", "#,##0")

# --- Marked --------------------------------------------------------------------------------------------------------------
MK = wb.create_sheet("Marked")
tr = pd.read_csv(D / "transaksjoner.csv")
MK["A1"] = "Sammenlignbare transaksjoner, Oslo-regionen 2024–2026 (pris per m² og brutto yield er egne beregninger)"; MK["A1"].font = BOLD
cols = ["Dato", "Eiendom", "Område", "Kjøper", "Selger", "Pris (NOK mill.)", "Areal (m2)", "Årlig leie (NOK mill.)", "Leietid (år)",
        "NOK per m²", "Brutto yield", "Kilde", "Merknad"]
head(MK, 3, cols)
for c, w in zip("ABCDEFGHIJKLM", (11, 40, 16, 18, 18, 10, 10, 10, 8, 10, 9, 36, 40)):
    MK.column_dimensions[c].width = w
for i, x in tr.iterrows():
    rr = 4 + i
    vals = [x["Dato"], x["Eiendom"], x["Område"], x["Kjøper"], x["Selger"], x["Pris (NOK mill.)"], x["Areal (m2)"],
            x["Årlig leie (NOK mill.)"], x["Leietid (år)"]]
    for j, v in enumerate(vals):
        c = MK.cell(row=rr, column=1 + j, value=None if pd.isna(v) else v)
        if j >= 5 and not pd.isna(v):
            c.font = BLUE; c.fill = INPUT
        c.alignment = WRAP
    MK[f"J{rr}"] = f'=IF(AND(ISNUMBER(F{rr}),ISNUMBER(G{rr})),F{rr}*1000000/G{rr},"")'; MK[f"J{rr}"].number_format = KR
    MK[f"K{rr}"] = f'=IF(AND(ISNUMBER(F{rr}),ISNUMBER(H{rr})),H{rr}/F{rr},"")'; MK[f"K{rr}"].number_format = PCT
    MK[f"L{rr}"] = x["Kilde"]; MK[f"M{rr}"] = x["Merknad"]
    for c in "LM":
        MK[f"{c}{rr}"].alignment = WRAP
TR_END = 3 + len(tr)
rr = TR_END + 2
MK[f"A{rr}"] = "Fugleåsen 7 ved budet"; MK[f"A{rr}"].font = BOLD
MK[f"F{rr}"] = f"={REF['pris']}"; MK[f"G{rr}"] = f"={REF['areal']}"; MK[f"H{rr}"] = "=Kontantstrøm!C11"
MK[f"J{rr}"] = f"=F{rr}*1000000/G{rr}"; MK[f"K{rr}"] = f"=H{rr}/F{rr}"
MK[f"J{rr}"].number_format = KR; MK[f"K{rr}"].number_format = PCT; MK[f"F{rr}"].number_format = MILL; MK[f"H{rr}"].number_format = MILL
FUG_ROW = rr
rr += 3
MK[f"A{rr}"] = "Markedsleie lager/logistikk per område, NOK/m²/år (Akershus Eiendom, Halvårsrapport høst 2026)"; MK[f"A{rr}"].font = BOLD
rr += 1
head(MK, rr, ["Område", "Lav", "Høy", "Midt"], col=2)
ml = pd.read_csv(D / "markedsleie_omrader.csv")
for i, x in ml.iterrows():
    q = rr + 1 + i
    MK[f"B{q}"] = x["Område"]; inp(MK[f"C{q}"], int(x["Lav (NOK/m2)"]), KR); inp(MK[f"D{q}"], int(x["Høy (NOK/m2)"]), KR)
    MK[f"E{q}"] = f"=(C{q}+D{q})/2"; MK[f"E{q}"].number_format = KR
q += 2
MK[f"B{q}"] = "Fugleåsen 7, kontraktsleie 2026"; MK[f"E{q}"] = f"={REF['leie26_m2']}"; MK[f"E{q}"].number_format = KR; MK[f"B{q}"].font = BOLD
MK[f"B{q + 1}"] = "PEF-porteføljen, snittleie"; MK[f"E{q + 1}"] = f"={REF['pef_leie_snitt']}"; MK[f"E{q + 1}"].number_format = KR

# --- Leietaker -----------------------------------------------------------------------------------------------------------
LT = wb.create_sheet("Leietaker")
LT.column_dimensions["A"].width = 52
nlp = pd.read_csv(D / "leietaker_regnskap.csv", index_col=0)
f7 = pd.read_csv(D / "fugleasen7_as_regnskap.csv", index_col=0)
LT["A1"] = "Norsk Lastbærer Pool AS (org.nr. 990043132), NOK mill. Kilde: Regnskapsregisteret (revidert, Deloitte)"; LT["A1"].font = BOLD
yrs = list(nlp.index)
head(LT, 3, ["Post"] + [str(y) for y in yrs])
poster = ["Driftsinntekter", "Lønnskostnad", "Sum driftskostnader", "Driftsresultat", "Finanskostnader", "Netto finans",
          "Resultat før skatt", "Årsresultat", "Sum eiendeler", "Anleggsmidler", "Omløpsmidler", "Bankinnskudd og kontanter",
          "Egenkapital", "Langsiktig gjeld", "Kortsiktig gjeld", "Sum gjeld"]
PR = {}
for i, p in enumerate(poster):
    q = 4 + i
    LT[f"A{q}"] = p; PR[p] = q
    for j, y in enumerate(yrs):
        inp(LT.cell(row=q, column=2 + j), float(nlp.loc[y, p]), MILL)
q = 5 + len(poster)
LT[f"A{q}"] = "Nøkkeltall"; LT[f"A{q}"].font = BOLD
LEIE_ROW = q + 1
LT[f"A{LEIE_ROW}"] = "Leie Fugleåsen 7 (eierselskapets driftsinntekter)"
for j, y in enumerate(yrs):
    inp(LT.cell(row=LEIE_ROW, column=2 + j), float(f7.loc[y, "Driftsinntekter"]), MILL)
nkl = [("Omsetningsvekst", lambda c, p: f"={c}{PR['Driftsinntekter']}/{p}{PR['Driftsinntekter']}-1" if p else None, "0.0%"),
       ("Driftsmargin", lambda c, p: f"={c}{PR['Driftsresultat']}/{c}{PR['Driftsinntekter']}", "0.0%"),
       ("Egenkapitalandel", lambda c, p: f"={c}{PR['Egenkapital']}/{c}{PR['Sum eiendeler']}", "0.0%"),
       ("Likviditetsgrad 1 (omløpsmidler / kortsiktig gjeld)", lambda c, p: f"={c}{PR['Omløpsmidler']}/{c}{PR['Kortsiktig gjeld']}", "0.00"),
       ("Rentedekning (driftsresultat / finanskostnader)", lambda c, p: f"={c}{PR['Driftsresultat']}/{c}{PR['Finanskostnader']}", "0.0x"),
       ("Gjeld / egenkapital", lambda c, p: f"={c}{PR['Sum gjeld']}/{c}{PR['Egenkapital']}", "0.00"),
       ("Leie Fugleåsen 7 / driftsinntekter", lambda c, p: f"={c}{LEIE_ROW}/{c}{PR['Driftsinntekter']}", "0.0%"),
       ("Leiedekning: (driftsresultat + leie) / leie", lambda c, p: f"=({c}{PR['Driftsresultat']}+{c}{LEIE_ROW})/{c}{LEIE_ROW}", "0.0x"),
       ("Kontanter / årlig leie", lambda c, p: f"={c}{PR['Bankinnskudd og kontanter']}/{c}{LEIE_ROW}", "0.0x")]
NLPR = {}
for i, (t, fx, f_) in enumerate(nkl):
    q = LEIE_ROW + 1 + i
    LT[f"A{q}"] = t; NLPR[t] = q
    for j in range(len(yrs)):
        c = L(2 + j); p = L(1 + j) if j > 0 else None
        LT[f"{c}{q}"] = fx(c, p); LT[f"{c}{q}"].number_format = f_
q += 2
LT[f"A{q}"] = "Fugleåsen 7 AS (org.nr. 999296947), eierselskapet, NOK mill."; LT[f"A{q}"].font = BOLD
q += 1
head(LT, q, ["Post"] + [str(y) for y in f7.index])
F7R = {}
for i, p in enumerate(["Driftsinntekter", "Sum driftskostnader", "Driftsresultat", "Sum eiendeler", "Egenkapital", "Sum gjeld"]):
    qq = q + 1 + i; LT[f"A{qq}"] = p; F7R[p] = qq
    for j, y in enumerate(f7.index):
        inp(LT.cell(row=qq, column=2 + j), float(f7.loc[y, p]), MILL)
qq += 1
LT[f"A{qq}"] = "Leie per m² (NOK)"
for j in range(len(f7.index)):
    c = L(2 + j); LT[f"{c}{qq}"] = f"={c}{F7R['Driftsinntekter']}*1000000/{REF['areal']}"; LT[f"{c}{qq}"].number_format = KR
qq += 1
LT[f"A{qq}"] = "Driftskostnader inkl. avskrivninger / inntekter"
for j in range(len(f7.index)):
    c = L(2 + j); LT[f"{c}{qq}"] = f"={c}{F7R['Sum driftskostnader']}/{c}{F7R['Driftsinntekter']}"; LT[f"{c}{qq}"].number_format = "0.0%"
for c in "BCD":
    LT.column_dimensions[c].width = 12

# --- Kontroller ------------------------------------------------------------------------------------------------------------
KO = wb.create_sheet("Kontroller")
KO.column_dimensions["A"].width = 70
ktr = [("NOI-dekomponering (sum av rad 18, skal være 0)", "=SUMPRODUCT(ABS(Kontantstrøm!C18:M18))"),
       ("Brutto leie = kontrakt + ny leie (skal være 0)", "=SUMPRODUCT(ABS(Kontantstrøm!C11:M11-Kontantstrøm!C7:M7*Kontantstrøm!C9:M9-Kontantstrøm!C8:M8*Kontantstrøm!C10:M10))"),
       ("Andeler ≤ 1 hvert år (antall brudd, skal være 0)", "=SUMPRODUCT(--(Kontantstrøm!C7:M7+Kontantstrøm!C8:M8>1.0000001))"),
       ("Lån inn = lån ut (skal være 0)", "=Kontantstrøm!B26+Kontantstrøm!L26"),
       ("Scenarioraden for 1 550 kr/m² og 5,8 % gir samme IRR som Kontantstrøm ved basisverdiene (skal være 0)",
        f"=ROUND(Scenarier!N{SROW[(1550, 0.058)]}-{NK['irr']},10)"),
       ("Maks bud ved krav gir IRR = krav (skal være 0)",
        f"=ROUND(NPV({REF['krav']},Kontantstrøm!C24:L24)/(1+{REF['kjopskost']})-{NK['maks']},8)")]
for i, (t, fx) in enumerate(ktr):
    KO[f"A{2 + i}"] = t; KO[f"B{2 + i}"] = fx; KO[f"B{2 + i}"].number_format = "0.000000"

OUT.parent.mkdir(parents=True, exist_ok=True)
wb.save(OUT)
print("skrev", OUT)
