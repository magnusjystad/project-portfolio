"""Laster ned Enovas energimerkeregister (Energimerkesystemet – Offentlige data) og trekker ut
(1) alle energiattester for de ti byggene i analysen og (2) fordelingen av beregnet levert energi per bygningskategori.

Krever en gratis API-nøkkel fra data.enova.no i miljøvariabelen ENOVA_API_KEY. Nøkkelen sendes som
spørreparameter (subscription-key), slik API-et støtter. Hele registeret lagres i data/kilde/enova/ (ikke i git).

    ENOVA_API_KEY=... python src/hent_enova.py
"""
import glob
import json
import os
import re
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "kilde" / "enova"
API = "https://api.data.enova.no/ems/offentlige-data"
KEY = os.environ.get("ENOVA_API_KEY", "")

# De ti byggene: adresse i registeret, gårds-/bruksnummer og organisasjonsnummer til eierselskapet (Brønnøysundregistrene)
BYGG = pd.DataFrame([
    ("Hoffsveien 70 B", "Hoffsveien 70 ?B", "32", "956", "895557722", "PEF II"),
    ("Hoffsveien 70 C", "Hoffsveien 70 ?C", "32", "957", "995557088", "PEF II"),
    ("Depotgata 22", "Depotgata 22", "83", "386", "890658792", "PEF II"),
    ("Hotvedtveien 6", "Hotvedtveien 6", "15", "100", "817660452", "PEF II"),
    ("Energivegen 2", "Energivegen 2", "7", "187", "914349486", "PEF II"),
    ("Industriveien 26", "Industriveien 26", "3", "413", "921675747", "PEF"),
    ("Karoline Eggens vei 3", "Karoline Eggens vei 3", "291", "40", "991299017", "PEF"),
    ("Stolvstadlia 9", "Stolvstadlia 9", "223", "35", "991422129", "PEF"),
    ("Nesoddveien 22", "Nesoddveien 22", "41|241", "8", "813723182", "PEF"),
    ("Toveien 28", "Toveien 28", "1", "44", "988613169", "PEF"),
], columns=["Eiendom", "adresse_regex", "gnr", "bnr", "orgnr", "Fond"])


def get(url):
    r = requests.get(url, params={"subscription-key": KEY}, timeout=120)
    r.raise_for_status()
    return r.json()["bankFileUrl"]


def download():
    RAW.mkdir(parents=True, exist_ok=True)
    for y in range(2010, 2026):
        (RAW / f"ems_{y}.csv").write_bytes(requests.get(get(f"{API}/v1/Fil/{y}"), timeout=900).content)
    for m in range(1, 13):
        try:
            (RAW / f"v2_2026_{m}.csv").write_bytes(requests.get(get(f"{API}/v2/Fil/2026/{m}"), timeout=900).content)
        except Exception as e:                                  # måneder som ikke finnes ennå
            print("2026", m, e)


def load():
    fr = []
    for f in sorted(glob.glob(str(RAW / "ems_*.csv"))) + sorted(glob.glob(str(RAW / "v2_2026_*.csv"))):
        d = pd.read_csv(f, dtype=str, encoding="utf-8-sig", on_bad_lines="skip")
        d["kildefil"] = Path(f).name
        fr.append(d)
    A = pd.concat(fr, ignore_index=True)
    A = A[~A["Bygningskategori"].isin(["Småhus", "Boligblokker"])].copy()
    A["kWh/m2"] = pd.to_numeric(A["BeregnetLevertEnergiTotaltkWhm2"], errors="coerce")
    A["Utstedt"] = pd.to_datetime(A["Utstedelsesdato"], errors="coerce", format="mixed")
    return A


if __name__ == "__main__":
    assert KEY, "Sett ENOVA_API_KEY"
    if not list(RAW.glob("ems_*.csv")):
        download()
    A = load()
    rows = []
    for _, b in BYGG.iterrows():
        m = A[A["GateAdresse"].fillna("").str.contains(b["adresse_regex"], case=False, regex=True)
              & A["Gnr"].fillna("").str.fullmatch(b["gnr"]) & (A["Bnr"] == b["bnr"])]
        m = m.assign(Eiendom=b["Eiendom"], Fond=b["Fond"], **{"Eier (org.nr. i Enhetsregisteret)": b["orgnr"]})
        rows.append(m)
    S = pd.concat(rows).drop_duplicates(["Attestnummer"]).sort_values(["Eiendom", "Bygningskategori", "Utstedt"])
    keep = ["Eiendom", "Fond", "Eier (org.nr. i Enhetsregisteret)", "GateAdresse", "Poststed", "Knr", "Gnr", "Bnr", "Bygningsnummer",
            "Organisasjonsnummer", "Bygningskategori", "Byggear", "Energikarakter", "Utstedt", "kWh/m2", "OppvarmetBra",
            "BeregnetVektetLevertEnergiReferanseklimaKWhm2", "Attestnummer", "kildefil"]
    S[keep].to_csv(ROOT / "data" / "energiattester_10_bygg.csv", index=False)
    # Fordeling i registeret: siste attest per bygning og kategori
    A["nokkel"] = A["Bygningsnummer"].fillna("") + "|" + A["Bygningskategori"].fillna("") + "|" + A["GateAdresse"].fillna("")
    L = A.sort_values("Utstedt").groupby("nokkel").tail(1)
    L = L[(L["kWh/m2"] > 10) & (L["kWh/m2"] < 1500)]
    q = L.groupby("Bygningskategori")["kWh/m2"].describe(percentiles=[0.10, 0.15, 0.25, 0.5, 0.75])
    q["Andel A"] = L.groupby("Bygningskategori")["Energikarakter"].apply(lambda s: (s == "A").mean())
    q["Andel A eller B"] = L.groupby("Bygningskategori")["Energikarakter"].apply(lambda s: s.isin(["A", "B"]).mean())
    q.to_csv(ROOT / "data" / "register_fordeling_per_kategori.csv")
    print(S[["Eiendom", "Bygningskategori", "Energikarakter", "Utstedt", "kWh/m2", "OppvarmetBra"]].to_string())
