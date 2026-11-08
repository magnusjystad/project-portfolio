"""Regner om Excel-modellen i LibreOffice og sammenligner med Python-modellen (src/modell.py):
nøkkeltall, NOI per år, hele sensitivitetsgitteret, kontrollene og de fire scenariene (ved å endre inndata).

    cd src && python sjekk_modell.py
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

import modell as Mo

ROOT = Path(__file__).resolve().parents[1]
XL = ROOT / "model" / "fugleasen7_investeringscase.xlsx"


def recalc(path):
    out = Path(tempfile.mkdtemp())
    subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(out), str(path)],
                   check=True, capture_output=True, timeout=300)
    return load_workbook(out / path.name, data_only=True)


def finn(ws, tekst, col="A"):
    for row in ws.iter_rows(min_col=1, max_col=1):
        if row[0].value == tekst:
            return row[0].row
    raise KeyError(tekst)


def nokkel(wb, navn):
    ws = wb["Kontantstrøm"]
    return ws[f"B{finn(ws, navn)}"].value


FEIL = []


def lik(navn, a, b, tol=1e-6):
    ok = a is not None and abs(a - b) <= tol * max(1.0, abs(b))
    print(f"{'OK ' if ok else 'AVVIK'} {navn}: Excel {a} / Python {b}")
    if not ok:
        FEIL.append(navn)


if __name__ == "__main__":
    X = Mo.run(); R = X["R"]
    wb = recalc(XL)
    # Ingen feilverdier noe sted
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith(("#", "Err:")):
                    FEIL.append(f"{ws.title}!{c.coordinate} {c.value}")
    F = wb["Forutsetninger"]
    lik("Maks bud ved 1 400 kr/m²", F[f"B{finn(F, 'Maks bud ved nedre markedsleie (1 400 kr/m²) og basis exit-yield (NOK mill.)')}"].value,
        Mo.resultat(None, markedsleie=Mo.M["markedsleie_langhus_lav"])["maks_bud"])
    lik("Bud", F[f"B{finn(F, 'Bud: avrundet ned til nærmeste 5 mill.')}"].value, X["pris"])
    for navn, py in [("IRR, ufinansiert", R["irr"]), ("IRR, egenkapital (belånt)", R["irr_belant"]),
                     ("Multippel, ufinansiert", R["multippel"]), ("Multippel, egenkapital", R["multippel_belant"]),
                     ("Netto startyield (NOI 2027 / kjøpesum)", R["netto_startyield"]), ("Kjøpesum per m² (NOK)", R["pris_m2"]),
                     ("Salgsverdi 2036 etter kostnader", R["exit"]), ("Maks bud ved avkastningskravet, basis", X["maks_bud"]),
                     ("Rentedekning år 1 (NOI / renter)", R["rentedekning_ar1"])]:
        lik(navn, nokkel(wb, navn), py, 1e-7)
    K = wb["Kontantstrøm"]
    noi_xl = [K.cell(row=14, column=3 + i).value for i in range(11)]
    lik("NOI 2027–2037 (maks avvik)", float(np.max(np.abs(np.array(noi_xl) - R["cf"]["Netto driftsinntekt"].values))), 0.0, 1e-9)
    # Sensitivitetsgitteret
    S = wb["Scenarier"]
    d_irr = d_bud = 0.0
    for row in S.iter_rows(min_row=4):
        ml, ey = row[0].value, row[1].value
        if ml is None:
            continue
        d_irr = max(d_irr, abs(row[13].value - X["grid"].loc[ml, ey]))
        d_bud = max(d_bud, abs(row[14].value - X["grid_bud"].loc[ml, ey]))
    lik("Gitter IRR (maks avvik)", d_irr, 0.0, 1e-7); lik("Gitter maks bud (maks avvik)", d_bud, 0.0, 1e-6)
    KO = wb["Kontroller"]
    for row in KO.iter_rows(min_row=2):
        if row[0].value:
            lik(f"Kontroll: {row[0].value}", row[1].value, 0.0, 1e-9)
    # Scenarier: endre inndata, regn om, sammenlign
    rad = {k: finn(F, t) for k, t in [("markedsleie", "Markedsleie ved reutleie, 2026-kroner"), ("ledighet_mnd", "Ledighet etter utløp"),
                                       ("utleiekost", "Utleiekostnad (megler, tilpasning), andel av første års leie"),
                                       ("exit_yield", "Exit-yield (netto)"), ("pris", "Kjøpesum (NOK mill.); standard = budet, kan overskrives")]}
    for navn in Mo.SCENARIER:
        over = Mo.scenario_over(navn, X["leie26_m2"])
        tmp = Path(tempfile.mkdtemp()) / XL.name
        shutil.copy(XL, tmp)
        w = load_workbook(tmp); f = w["Forutsetninger"]
        for k, v in over.items():
            f[f"B{rad[k]}"] = v
        f[f"B{rad['pris']}"] = X["pris"]
        w.save(tmp)
        r = recalc(tmp)
        lik(f"Scenario «{navn}» IRR", nokkel(r, "IRR, ufinansiert"), X["scenarier"].loc[navn, "IRR"], 1e-7)
        lik(f"Scenario «{navn}» IRR belånt", nokkel(r, "IRR, egenkapital (belånt)"), X["scenarier"].loc[navn, "IRR belånt"], 1e-7)
        lik(f"Scenario «{navn}» maks bud", nokkel(r, "Maks bud ved avkastningskravet, basis"), X["scenarier"].loc[navn, "Maks bud"], 1e-7)
    print("\nALLE KONTROLLER OK" if not FEIL else f"\n{len(FEIL)} FEIL: {FEIL}")
