"""Trekker ut CRREM 1,5 °C-baner (V2.05) for Norge for bygningstypene i analysen.

Kilde: Carbon Risk Real Estate Monitor (CRREM), www.crrem.org, «CRREM Pathways V2.05» (2026). Filen lastes ned fra
crrem.org (gratis registrering) og legges i data/kilde/crrem_pathways_v2.05.xlsx. Vilkårene tillater ikke videreformidling
av selve datasettet, så bare banene som brukes her lagres i data/crrem_norge.csv.

    python src/crrem.py
"""
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
TYPER = ["Office", "Retail Warehouse", "Retail High Street", "Distribution Warehouse Warm"]


def read(sheet):
    wb = load_workbook(ROOT / "data" / "kilde" / "crrem_pathways_v2.05.xlsx", read_only=True, data_only=True)
    rows = list(wb[sheet].iter_rows(min_row=5, values_only=True))
    hdr = rows[0]
    d = pd.DataFrame(rows[1:], columns=hdr)
    d = d[(d["Country"] == "Norway") & d["Property Type"].isin(TYPER)]
    years = [c for c in hdr if isinstance(c, int)]
    return d.set_index("Property Type")[years]


if __name__ == "__main__":
    eui, co2 = read("EUI Pathways kWh (sqm)"), read("CO2 Pathways (sqm)")
    out = pd.concat({"kWh/m2": eui, "kgCO2/m2": co2}, names=["Måleenhet", "Bygningstype"]).T
    out.index.name = "År"
    out.to_csv(ROOT / "data" / "crrem_norge.csv")
    print(out.loc[[2025, 2030, 2035, 2040, 2050]].round(1).T)
