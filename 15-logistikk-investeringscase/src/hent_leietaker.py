"""Henter regnskapstall fra Regnskapsregisteret (Brønnøysundregistrene, åpent API) for
  - leietakeren Norsk Lastbærer Pool AS (org.nr. 990043132) -> data/leietaker_regnskap.csv
  - eiendomsselskapet Fugleåsen 7 AS (org.nr. 999296947)   -> data/fugleasen7_as_regnskap.csv
Tall i NOK mill. Rådata lagres i data/kilde/ og brukes om API-et ikke svarer.

    python src/hent_leietaker.py
"""
import json
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
SELSKAP = {"990043132": "leietaker_regnskap.csv", "999296947": "fugleasen7_as_regnskap.csv"}


def hent(org):
    raw = ROOT / "data" / "kilde" / f"regnskap_{org}_brreg.json"
    try:
        r = requests.get(f"https://data.brreg.no/regnskapsregisteret/regnskap/{org}", timeout=60)
        r.raise_for_status()
        raw.write_text(r.text)
    except Exception as e:
        print(org, "bruker lagret kopi:", e)
    rows = []
    for x in json.loads(raw.read_text()):
        res, ek, e = x["resultatregnskapResultat"], x["egenkapitalGjeld"], x["eiendeler"]
        dr, fi = res["driftsresultat"], res["finansresultat"]
        rows.append({"År": int(x["regnskapsperiode"]["tilDato"][:4]),
                     "Driftsinntekter": dr["driftsinntekter"]["sumDriftsinntekter"],
                     "Lønnskostnad": dr["driftskostnad"].get("loennskostnad", 0.0),
                     "Sum driftskostnader": dr["driftskostnad"]["sumDriftskostnad"],
                     "Driftsresultat": dr["driftsresultat"],
                     "Finanskostnader": fi["finanskostnad"].get("sumFinanskostnad", 0.0),
                     "Netto finans": fi["nettoFinans"],
                     "Resultat før skatt": res["ordinaertResultatFoerSkattekostnad"],
                     "Årsresultat": res["aarsresultat"],
                     "Sum eiendeler": e["sumEiendeler"], "Anleggsmidler": e["anleggsmidler"]["sumAnleggsmidler"],
                     "Omløpsmidler": e["omloepsmidler"]["sumOmloepsmidler"], "Bankinnskudd og kontanter": e["sumBankinnskuddOgKontanter"],
                     "Egenkapital": ek["egenkapital"]["sumEgenkapital"], "Langsiktig gjeld": ek["gjeldOversikt"]["langsiktigGjeld"]["sumLangsiktigGjeld"],
                     "Kortsiktig gjeld": ek["gjeldOversikt"]["kortsiktigGjeld"]["sumKortsiktigGjeld"], "Sum gjeld": ek["gjeldOversikt"]["sumGjeld"],
                     "Revisjon": "revidert" if not x["revisjon"]["ikkeRevidertAarsregnskap"] else "ikke revidert"})
    d = pd.DataFrame(rows).sort_values("År").set_index("År")
    num = d.drop(columns="Revisjon") / 1e6
    num["Revisjon"] = d["Revisjon"]
    return num


if __name__ == "__main__":
    for org, fil in SELSKAP.items():
        d = hent(org)
        d.to_csv(ROOT / "data" / fil)
        print(org, "\n", d.drop(columns="Revisjon").round(2).T)
