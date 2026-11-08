"""Regner om model/energi_klima_modell.xlsx i LibreOffice og sammenligner med src/analyse.py.

    python src/sjekk_modell.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import load_workbook

import analyse as A

ROOT = Path(__file__).resolve().parents[1]

if __name__ == "__main__":
    out = Path(tempfile.mkdtemp())
    subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(out), str(ROOT / "model" / "energi_klima_modell.xlsx")],
                   check=True, capture_output=True, timeout=300)
    wb = load_workbook(out / "energi_klima_modell.xlsx", data_only=True)
    R = A.run()
    ok = True
    B = {r[0]: r for r in wb["Bygg"].iter_rows(min_row=2, values_only=True) if r[0]}
    for e, r in R["bygg"].iterrows():
        for col, idx in [("Energibruk (MWh/år)", 8), ("Reduksjon til taksonomigrensen (kWh/m2)", 14), ("Reduksjon til CRREM 2030 (kWh/m2)", 15)]:
            good = abs(B[e][idx] - r[col]) < 1e-6
            ok &= good
            if not good:
                print("AVVIK", e, col, B[e][idx], r[col])
    T = [r for r in wb["Tiltaksplan"].iter_rows(min_row=4, values_only=True) if r[0] and r[1] in ("1", "2")]
    inv_x = sum(r[10] for r in T)
    inv_p = R["tiltak"]["Investering (MNOK)"].sum()
    print(f"Investering nivå 1+2: Excel {inv_x:.4f} / Python {inv_p:.4f} MNOK")
    ok &= abs(inv_x - inv_p) < 1e-6
    S = [r for r in wb["Solceller"].iter_rows(min_row=4, values_only=True) if r[0]]
    for r in S:
        good = abs(r[6] - R["sol"].loc[r[0], "Tilbakebetaling 2025-pris (år)"]) < 1e-6
        ok &= good
    tax_x = {(r[0], r[1]): r[11] for r in wb["Taksonomi"].iter_rows(min_row=2, values_only=True) if r[0]}
    for _, r in R["attester"].iterrows():
        ok &= tax_x[(r["Eiendom"], r["Bygningskategori"])] == bool(r["Taksonomiforenlig (energikriteriet)"])
    print("ALLE KONTROLLER OK" if ok else "KONTROLL FEILET")
    sys.exit(0 if ok else 1)
