"""Lager model/energi_klima_modell.xlsx: byggdata, taksonomitest, CRREM-sammenligning, tiltaksplan og solceller med
Excel-formler. Inndata er blå på gul bakgrunn; alt annet er formler. src/sjekk_modell.py kontrollerer mot src/analyse.py.

    python src/lag_modell.py
"""
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as L

import analyse as A

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "model" / "energi_klima_modell.xlsx"
R = A.run()
BLUE, BOLD = Font(color="1F4E79"), Font(bold=True)
INPUT = PatternFill("solid", fgColor="FFF4D6")
HEAD = PatternFill("solid", fgColor="E8ECF2")
WRAP = Alignment(wrap_text=True, vertical="top")
wb = Workbook()


def sheet(name, wa=34, w=14):
    ws = wb.create_sheet(name)
    ws.column_dimensions["A"].width = wa
    for c in range(2, 30):
        ws.column_dimensions[L(c)].width = w
    return ws


def header(ws, row, labels):
    for j, h in enumerate(labels):
        c = ws.cell(row=row, column=1 + j, value=h)
        c.font = BOLD; c.fill = HEAD; c.alignment = WRAP
    ws.row_dimensions[row].height = 45


def inp(c, v, fmt=None):
    c.value = v; c.font = BLUE; c.fill = INPUT
    if fmt:
        c.number_format = fmt


# --- Forutsetninger ------------------------------------------------------------------------------------------------
F = wb.active; F.title = "Forutsetninger"; F.column_dimensions["A"].width = 70; F.column_dimensions["B"].width = 14
F["A1"] = "Forutsetninger (blå på gul = inndata, med kilde)"; F["A1"].font = BOLD
fz = [("spot25", "Spotpris NO1 2025, snitt (øre/kWh eks. mva.; Nord Pool via hvakosterstrommen.no)", R["spot"]["2025"], "0.0"),
      ("spot26", "Spotpris NO1 2026 hittil (øre/kWh)", R["spot"]["2026 hittil"], "0.0"),
      ("nett", "Elvia energiledd, næring >100 MWh lavspent fra 1.7.2026 (øre/kWh)", A.ELVIA_ENERGILEDD, "0.00"),
      ("avgift", "Elavgift 2026, alminnelig sats (øre/kWh; Skatteetaten)", A.ELAVGIFT, "0.00"),
      ("ef_nve", "Utslippsfaktor strøm, NVE klimadeklarasjon 2025 (g CO2e/kWh)", A.EF["NVE 2025 (lokasjonsbasert)"], "0.0"),
      ("ef_eu", "Utslippsfaktor strøm, europeisk miks NS 3720 scenario 2 (g CO2e/kWh)", A.EF["Europeisk miks (NS 3720)"], "0.0"),
      ("ef_crrem", "CRREM V2.05 utslippsfaktor Norge 2025 (kg CO2e/kWh)", float(A.crrem_ef().loc[2025]), "0.00000"),
      ("sol_kr", "Solceller store flate tak: investering (kr/kWp; NVE 2026)", A.SOL["kr/kWp"], "#,##0"),
      ("sol_kwh", "Solceller: produksjon (kWh/kWp; NVE 2026)", A.SOL["kWh/kWp"], "#,##0"),
      ("sol_drift", "Solceller: drift (kr/kW/år; NVE 2026)", A.SOL["drift kr/kW/år"], "0.0"),
      ("sol_ratio", "Solceller: kWp per m² oppvarmet areal (median av PEF-lagrene med anlegg)", R["sol_ratio"], "0.000"),
      ("stotte", "Enova-støtte i følsomhet (andel av investering; Hoffsveien 70 B/C fikk 30 %)", 0.30, "0%")]
REF = {}
for i, (k, lab, v, fmt) in enumerate(fz):
    F[f"A{3 + i}"] = lab; inp(F[f"B{3 + i}"], v, fmt); REF[k] = f"Forutsetninger!$B${3 + i}"
r0 = 4 + len(fz)
F[f"A{r0}"] = "Strømpris 2025 inkl. nett og avgift (kr/kWh)"; F[f"B{r0}"] = f"=({REF['spot25']}+{REF['nett']}+{REF['avgift']})/100"
F[f"A{r0 + 1}"] = "Strømpris 2026 hittil inkl. nett og avgift (kr/kWh)"; F[f"B{r0 + 1}"] = f"=({REF['spot26']}+{REF['nett']}+{REF['avgift']})/100"
for rr in (r0, r0 + 1):
    F[f"B{rr}"].number_format = "0.000"; F[f"B{rr}"].font = BOLD
REF["p25"], REF["p26"] = f"Forutsetninger!$B${r0}", f"Forutsetninger!$B${r0 + 1}"
F[f"A{r0 + 3}"] = "Taksonomi 7.7, topp 15 % (kWh/m²·år), Finans Norges veileder juni 2026, Vedlegg B"; F[f"A{r0 + 3}"].font = BOLD
header_row = r0 + 4
for j, h in enumerate(["Kategori", "Ny metode (vektet)", "Gammel metode"]):
    c = F.cell(row=header_row, column=1 + j, value=h); c.font = BOLD; c.fill = HEAD
TROW = {}
for i, kat in enumerate(["Kontorbygg", "Forretningsbygg", "Lett industri, verksteder"]):
    rr = header_row + 1 + i
    F[f"A{rr}"] = kat; inp(F[f"B{rr}"], A.TOPP15[(kat, "ny")]); inp(F[f"C{rr}"], A.TOPP15[(kat, "gammel")])
    TROW[kat] = rr
TAB = f"Forutsetninger!$A${header_row + 1}:$C${header_row + 3}"

# --- CRREM ---------------------------------------------------------------------------------------------------------------
eui, co2 = R["eui"], R["co2"]
C = sheet("CRREM", 10, 16)
C["A1"] = "CRREM 1,5 °C-baner for Norge, V2.05 (Carbon Risk Real Estate Monitor, www.crrem.org)"; C["A1"].font = BOLD
types = list(eui.columns)
header(C, 3, ["År"] + [f"{t} kWh/m²" for t in types] + [f"{t} kgCO2/m²" for t in types] + ["Utslippsfaktor Norge (kg/kWh)"])
ef = A.crrem_ef()
for i, y in enumerate(eui.index):
    rr = 4 + i
    inp(C.cell(row=rr, column=1), int(y))
    for j, t in enumerate(types):
        inp(C.cell(row=rr, column=2 + j), float(eui.loc[y, t]), "0.0")
        inp(C.cell(row=rr, column=2 + len(types) + j), float(co2.loc[y, t]), "0.00")
    inp(C.cell(row=rr, column=2 + 2 * len(types)), float(ef.loc[y]) if y in ef.index else None, "0.00000")
CLAST = 3 + len(eui.index)
CEUI = {t: f"CRREM!${L(2 + j)}$4:${L(2 + j)}${CLAST}" for j, t in enumerate(types)}
CYR = f"CRREM!$A$4:$A${CLAST}"

# --- Attester (taksonomitest per bygningsdel) -------------------------------------------------------------------------------
At = sheet("Taksonomi", 24, 14)
a = R["attester"].sort_values(["Eiendom", "Bygningskategori"]).reset_index(drop=True)
cols = ["Eiendom", "Bygningskategori", "Energikarakter", "Utstedt", "Metode", "Levert energi (kWh/m²)", "Vektet levert energi (kWh/m²)",
        "Testverdi", "Topp 15 %-grense", "Energimerke A", "Under grensen", "Taksonomiforenlig (energi)", "Mangler til grensen (kWh/m²)", "Attest gyldig til"]
header(At, 1, cols)
for i, r_ in a.iterrows():
    rr = 2 + i
    inp(At[f"A{rr}"], r_["Eiendom"]); inp(At[f"B{rr}"], r_["Bygningskategori"]); inp(At[f"C{rr}"], r_["Energikarakter"])
    inp(At[f"D{rr}"], r_["Utstedt"].to_pydatetime(), "yyyy-mm-dd")
    At[f"E{rr}"] = f'=IF(D{rr}>=DATE(2026,1,1),"ny","gammel")'
    inp(At[f"F{rr}"], float(r_["kWh/m2"]), "0.0")
    inp(At[f"G{rr}"], None if pd.isna(r_["BeregnetVektetLevertEnergiReferanseklimaKWhm2"]) else float(r_["BeregnetVektetLevertEnergiReferanseklimaKWhm2"]), "0.0")
    At[f"H{rr}"] = f'=IF(E{rr}="ny",G{rr},F{rr})'; At[f"H{rr}"].number_format = "0.0"
    At[f"I{rr}"] = f'=VLOOKUP(B{rr},{TAB},IF(E{rr}="ny",2,3),FALSE)'
    At[f"J{rr}"] = f'=C{rr}="A"'; At[f"K{rr}"] = f"=H{rr}<=I{rr}"; At[f"L{rr}"] = f"=OR(J{rr},K{rr})"
    At[f"M{rr}"] = f"=IF(L{rr},0,H{rr}-I{rr})"; At[f"M{rr}"].number_format = "0.0"
    At[f"N{rr}"] = f"=EDATE(D{rr},120)"; At[f"N{rr}"].number_format = "yyyy-mm-dd"
ALAST = 1 + len(a)
At.freeze_panes = "C2"

# --- Bygg ------------------------------------------------------------------------------------------------------------------
B = sheet("Bygg", 24, 14)
b = R["bygg"]
bcols = ["Eiendom", "Fond", "Segment", "Hoveddel (attestkategori)", "CRREM-type", "Oppvarmet BRA (m²)", "Levert energi (kWh/m²)", "Grunnlag",
         "Energibruk (MWh/år)", "Utslipp NVE 2025 (tCO2e)", "Utslipp europeisk miks (tCO2e)", "CRREM 2030 (kWh/m²)", "Over CRREM energibanen fra (år)",
         "CO2-intensitet CRREM-faktor 2025 (kg/m²)", "Mangler til taksonomigrensen, hoveddel (kWh/m²)", "Mangler til CRREM 2030 (kWh/m²)",
         "Solceller i dag (kWp)", "Solproduksjon i dag (MWh/år)"]
header(B, 1, bcols)
HOVED = A.HOVED
BROW = {}
for i, (e, r_) in enumerate(b.iterrows()):
    rr = 2 + i; BROW[e] = rr
    inp(B[f"A{rr}"], e); inp(B[f"B{rr}"], r_["Fond"]); inp(B[f"C{rr}"], r_["Segment"]); inp(B[f"D{rr}"], HOVED[r_["Segment"]]); inp(B[f"E{rr}"], r_["CRREM-type"])
    inp(B[f"F{rr}"], float(r_["Oppvarmet BRA (m2)"]), "#,##0"); inp(B[f"G{rr}"], float(r_["Levert energi (kWh/m2)"]), "0.0"); B[f"H{rr}"] = r_["Grunnlag"]
    B[f"I{rr}"] = f"=G{rr}*F{rr}/1000"; B[f"I{rr}"].number_format = "#,##0"
    B[f"J{rr}"] = f"=I{rr}*{REF['ef_nve']}/1000"; B[f"J{rr}"].number_format = "0.0"
    B[f"K{rr}"] = f"=I{rr}*{REF['ef_eu']}/1000"; B[f"K{rr}"].number_format = "#,##0"
    col = CEUI[r_["CRREM-type"]]
    B[f"L{rr}"] = f"=INDEX({col},MATCH(2030,{CYR},0))"; B[f"L{rr}"].number_format = "0.0"
    B[f"M{rr}"] = f'=IFERROR(INDEX({CYR},MATCH(1,INDEX(--({col}<G{rr}),0),0)),"etter 2050")'
    B[f"N{rr}"] = f"=G{rr}*{REF['ef_crrem']}"; B[f"N{rr}"].number_format = "0.00"
    B[f"O{rr}"] = (f'=SUMIFS(Taksonomi!$M$2:$M${ALAST},Taksonomi!$A$2:$A${ALAST},A{rr},Taksonomi!$B$2:$B${ALAST},D{rr})')
    B[f"O{rr}"].number_format = "0.0"
    B[f"P{rr}"] = f"=MAX(0,G{rr}-L{rr})"; B[f"P{rr}"].number_format = "0.0"
    inp(B[f"Q{rr}"], float(r_["Solceller (kWp)"]), "#,##0"); inp(B[f"R{rr}"], float(r_["Solproduksjon (MWh/år)"]), "#,##0")
BLAST = 1 + len(b)
B[f"A{BLAST + 1}"] = "Sum / snitt"; B[f"A{BLAST + 1}"].font = BOLD
for c in "FIJKQR":
    B[f"{c}{BLAST + 1}"] = f"=SUM({c}2:{c}{BLAST})"; B[f"{c}{BLAST + 1}"].number_format = "#,##0"; B[f"{c}{BLAST + 1}"].font = BOLD
B[f"G{BLAST + 1}"] = f"=I{BLAST + 1}/F{BLAST + 1}*1000"; B[f"G{BLAST + 1}"].number_format = "0.0"
B.freeze_panes = "B2"

# --- Enova-kostnader ------------------------------------------------------------------------------------------------------------
E = sheet("Enova-kostnader", 40, 16)
E["A1"] = "Enova, energitilskuddsordningen: kostnad og energiresultat første år (Stortinget Dok. 15:1032 (2024–2025), tabell 2)"; E["A1"].font = BOLD
header(E, 3, ["Tiltak", "Kostnad (kr)", "kWh første år", "kr per årlig kWh"])
EROW = {}
for i, (t, r_) in enumerate(A.ENOVA.iterrows()):
    rr = 4 + i; EROW[t] = rr
    E[f"A{rr}"] = t; inp(E[f"B{rr}"], int(r_["Kostnad (kr)"]), "#,##0"); inp(E[f"C{rr}"], int(r_["kWh første år"]), "#,##0")
    E[f"D{rr}"] = f"=B{rr}/C{rr}"; E[f"D{rr}"].number_format = "0.00"

# --- Tiltaksplan ------------------------------------------------------------------------------------------------------------------
T = sheet("Tiltaksplan", 22, 14)
T["A1"] = "Tiltaksplan: nivå 1 = til taksonomigrensen (topp 15 %); nivå 2 = videre ned til CRREM-banen for 2030"; T["A1"].font = BOLD
tcols = ["Eiendom", "Nivå", "Tiltak 1", "Tiltak 2", "Tiltak 3", "Tiltak 4", "Enhetskostnad (kr per årlig kWh)", "Reduksjon (kWh/m²)",
         "Andel av dagens energibruk", "Besparelse (MWh/år)", "Investering (MNOK)", "Årlig besparelse 2025-pris (MNOK)",
         "Tilbakebetaling 2025-pris (år)", "Tilbakebetaling 2026-pris (år)", "Tilbakebetaling med Enova-støtte, 2025-pris (år)",
         "Utslippskutt NVE 2025 (tCO2e/år)", "Utslippskutt europeisk miks (tCO2e/år)"]
header(T, 3, tcols)
rr = 4
for e, pk in A.PAKKE.items():
    for niva in ("1", "2"):
        br = BROW[e]
        T[f"A{rr}"] = e; T[f"B{rr}"] = niva
        for j in range(4):
            T.cell(row=rr, column=3 + j, value=pk[j] if j < len(pk) else None)
        cost = "+".join(f'IFERROR(VLOOKUP({L(3 + j)}{rr},\'Enova-kostnader\'!$A$4:$C$15,2,FALSE),0)' for j in range(4))
        kwh = "+".join(f'IFERROR(VLOOKUP({L(3 + j)}{rr},\'Enova-kostnader\'!$A$4:$C$15,3,FALSE),0)' for j in range(4))
        T[f"G{rr}"] = f"=({cost})/({kwh})"; T[f"G{rr}"].number_format = "0.00"
        T[f"H{rr}"] = f"=Bygg!O{br}" if niva == "1" else f"=MAX(0,Bygg!P{br}-Bygg!O{br})"; T[f"H{rr}"].number_format = "0.0"
        T[f"I{rr}"] = f"=H{rr}/Bygg!G{br}"; T[f"I{rr}"].number_format = "0%"
        T[f"J{rr}"] = f"=H{rr}*Bygg!F{br}/1000"; T[f"J{rr}"].number_format = "#,##0"
        T[f"K{rr}"] = f"=J{rr}*1000*G{rr}/1000000"; T[f"K{rr}"].number_format = "0.00"
        T[f"L{rr}"] = f"=J{rr}*1000*{REF['p25']}/1000000"; T[f"L{rr}"].number_format = "0.00"
        T[f"M{rr}"] = f"=G{rr}/{REF['p25']}"; T[f"N{rr}"] = f"=G{rr}/{REF['p26']}"; T[f"O{rr}"] = f"=(1-{REF['stotte']})*G{rr}/{REF['p25']}"
        for c in "MNO":
            T[f"{c}{rr}"].number_format = "0.0"
        T[f"P{rr}"] = f"=J{rr}*{REF['ef_nve']}/1000"; T[f"P{rr}"].number_format = "0.0"
        T[f"Q{rr}"] = f"=J{rr}*{REF['ef_eu']}/1000"; T[f"Q{rr}"].number_format = "#,##0"
        rr += 1
TLAST = rr - 1
T[f"A{rr}"] = "Sum nivå 1"; T[f"A{rr + 1}"] = "Sum nivå 1 + 2"
for c in "JKLPQ":
    T[f"{c}{rr}"] = f'=SUMIF($B$4:$B${TLAST},"1",{c}4:{c}{TLAST})'; T[f"{c}{rr + 1}"] = f"=SUM({c}4:{c}{TLAST})"
    for x in (rr, rr + 1):
        T[f"{c}{x}"].number_format = "#,##0.0"; T[f"{c}{x}"].font = BOLD
T.freeze_panes = "C4"

# --- Solceller -------------------------------------------------------------------------------------------------------------------
S = sheet("Solceller", 24, 16)
S["A1"] = "Nye solcelleanlegg på bygg uten anlegg i dag (kapasitet skalert med PEF-lagrenes kWp per m²)"; S["A1"].font = BOLD
header(S, 3, ["Eiendom", "Oppvarmet BRA (m²)", "kWp", "Produksjon (MWh/år)", "Investering (MNOK)", "Netto årlig verdi 2025-pris (MNOK)",
              "Tilbakebetaling 2025-pris (år)", "Tilbakebetaling 2026-pris (år)"])
for i, e in enumerate(A.SOL_NYTT):
    rr = 4 + i; br = BROW[e]
    S[f"A{rr}"] = e; S[f"B{rr}"] = f"=Bygg!F{br}"
    S[f"C{rr}"] = f"=B{rr}*{REF['sol_ratio']}"; S[f"D{rr}"] = f"=C{rr}*{REF['sol_kwh']}/1000"
    S[f"E{rr}"] = f"=C{rr}*{REF['sol_kr']}/1000000"
    S[f"F{rr}"] = f"=(D{rr}*1000*{REF['p25']}-C{rr}*{REF['sol_drift']})/1000000"
    S[f"G{rr}"] = f"=E{rr}/F{rr}"; S[f"H{rr}"] = f"=E{rr}*1000000/(D{rr}*1000*{REF['p26']}-C{rr}*{REF['sol_drift']})"
    for c, fmt in zip("BCDEFGH", ["#,##0", "#,##0", "#,##0", "0.00", "0.00", "0.0", "0.0"]):
        S[f"{c}{rr}"].number_format = fmt

OUT.parent.mkdir(exist_ok=True)
wb.save(OUT)
print("skrev", OUT)
