"""Referansemodell (Python) for investeringscaset Fugleåsen 7, Langhus. Excel-modellen (lag_modell.py) bygger
den samme kontantstrømmen med formler, og sjekk_modell.py sammenligner de to.

Markedsdata og fakta leses fra data/markedsdata.csv (med kilde per linje). Antagelser står samlet i ANTAGELSER
under, med begrunnelse; ingen av dem er observerte tall.

    python src/modell.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
M = pd.read_csv(D / "markedsdata.csv").set_index("Nøkkel")["Verdi"].astype(float).to_dict()

# --- Antagelser (ikke observerte tall) ---------------------------------------------------------------------------------
ANTAGELSER = {
    "kjop_aar": 2026,            # oppgjør 31.12.2026
    "holdetid": 10,              # salg 31.12.2036
    "kpi_andel": 1.00,           # leien reguleres med 100 % av KPI (Finanstilsynet: «vanligvis årlig med … KPI»)
    "markedsleie": 1550,         # NOK/m², midt i Akershus Eiendoms intervall for Langhus (1 400–1 700)
    "ledighet_mnd": 6,           # måneder tomt etter utløp før ny leietaker
    "utleiekost": 0.15,          # megler og leietakertilpasning, andel av første års nye leie
    "eierkost": M["eierkostnad_skatteetaten"],   # 10 % av brutto leie (Skatteetatens sjablong)
    "exit_yield": M["pef_netto_yield"],          # 5,8 %: netto yield i PEFs siste verdivurdering
    "kjopskost": 0.01, "salgskost": 0.01,       # transaksjonskostnader (selskapssalg, ingen dokumentavgift)
    "krav": 0.075,               # avkastningskrav, se README (prime 5,5 % + 2 % KPI; 10-års stat 4,4 % + 3 % premie)
    "ltv": 0.55, "rente": M["bankrente_naeringseiendom"],   # avdragsfritt lån; rente fra Newsec høst 2026
}


def kpi(aar):
    return {2025: M["kpi_nov_2025"], 2026: M["kpi_2026"], 2027: M["kpi_2027"], 2028: M["kpi_2028"],
            2029: M["kpi_2029"]}.get(aar, M["kpi_lang"])


def kontantstrom(**over):
    """Årlig kontantstrøm for årene etter kjøp til og med året etter salg (til exit-verdien). NOK mill."""
    a = {**ANTAGELSER, **over}
    k0, n = a["kjop_aar"], a["holdetid"]
    areal = M["areal"]
    utlop = M["leieavtale_start"] + M["leieavtale_lengde"]           # 2033,75
    ny_start = utlop + a["ledighet_mnd"] / 12
    aar = list(range(k0 + 1, k0 + n + 2))
    # Indeks: leien i år t reguleres med KPI for år t-1 (proxy for novembertallet)
    idx, I = {2026: 1.0}, 1.0
    for y in range(2027, aar[-1] + 1):
        I *= 1 + a["kpi_andel"] * kpi(y - 1); idx[y] = I
    leie26 = M["leie_2025"] * (1 + a["kpi_andel"] * M["kpi_nov_2025"])
    rows = []
    for y in aar:
        f_k = max(0.0, min(1.0, utlop - y))                           # andel av året med NLP-kontrakten
        f_n = max(0.0, min(1.0, y + 1 - ny_start))                     # andel av året med ny leietaker
        kontrakt = leie26 * idx[y]
        marked = a["markedsleie"] * areal * idx[y] / 1e6               # markedsleie for hele bygget, NOK mill.
        brutto = f_k * kontrakt + f_n * marked
        eier = a["eierkost"] * (f_k * kontrakt + (1 - f_k) * marked)
        utleie = a["utleiekost"] * marked if y <= ny_start < y + 1 else 0.0
        rows.append({"År": y, "Indeks": idx[y], "Andel kontrakt": f_k, "Andel ny leie": f_n, "Kontraktsleie (100 %)": kontrakt,
                     "Markedsleie (100 %)": marked, "Brutto leie": brutto, "Eierkostnader": eier, "Utleiekostnader": utleie,
                     "Netto driftsinntekt": brutto - eier - utleie})
    return pd.DataFrame(rows).set_index("År"), a


def resultat(pris=None, **over):
    cf, a = kontantstrom(**over)
    hold = cf.index[:-1]
    noi = cf["Netto driftsinntekt"]
    exit_v = noi.iloc[-1] / a["exit_yield"] * (1 - a["salgskost"])
    flows = noi.loc[hold].values.copy()
    flows[-1] += exit_v
    t = np.arange(1, len(flows) + 1)
    maks = float(np.sum(flows / (1 + a["krav"]) ** t)) / (1 + a["kjopskost"])
    pris = maks if pris is None else pris
    ufin = np.r_[-pris * (1 + a["kjopskost"]), flows]
    lan = a["ltv"] * pris
    fin = ufin.copy(); fin[0] += lan; fin[1:] -= lan * a["rente"]; fin[-1] -= lan
    noi1 = noi.iloc[0]
    return {"cf": cf, "a": a, "exit": exit_v, "maks_bud": maks, "pris": pris, "irr": irr(ufin), "irr_belant": irr(fin),
            "multippel": ufin[1:].sum() / -ufin[0], "multippel_belant": fin[1:].sum() / -fin[0],
            "netto_startyield": noi1 / pris, "pris_m2": pris * 1e6 / M["areal"], "ufin": ufin, "fin": fin,
            "rentedekning_ar1": noi1 / (lan * a["rente"])}


def irr(c):
    lo, hi = -0.99, 1.0
    f = lambda r: sum(x / (1 + r) ** i for i, x in enumerate(c))
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) > 0 else (lo, mid)
    return (lo + hi) / 2


def bud():
    """Budet: maks pris ved avkastningskravet når reutleien skjer til nedre del av markedsleien på Langhus
    (1 400 kr/m²), avrundet ned til nærmeste 5 mill. Da betaler vi ikke for mer av reutleiegevinsten enn den
    forsiktige delen av intervallet gir."""
    return float(np.floor(resultat(None, markedsleie=M["markedsleie_langhus_lav"])["maks_bud"] / 5) * 5)


LEIEGRID = [1300, 1400, 1500, 1550, 1600, 1700, 1800]
YIELDGRID = [0.0525, 0.055, 0.0575, 0.058, 0.060, 0.0625, 0.065]
SCENARIER = {
    "Basis: reutleie etter 6 mnd": {},
    "NLP fornyer til markedsleie": {"ledighet_mnd": 0, "utleiekost": 0.05},
    "NLP fornyer til dagens leie": {"ledighet_mnd": 0, "utleiekost": 0.0, "markedsleie": None},
    "Svak: 12 mnd ledig, 1 400 kr/m², exit 6,25 %": {"ledighet_mnd": 12, "markedsleie": 1400, "exit_yield": 0.0625},
}


def scenario_over(navn, pris_kontrakt_m2):
    o = dict(SCENARIER[navn])
    if "markedsleie" in o and o["markedsleie"] is None:
        o["markedsleie"] = pris_kontrakt_m2
    return o


def run():
    base = resultat()
    pris = bud()
    R = resultat(pris)
    # Dagens leie per m² i 2026-kroner (brukes i fornyelse-til-dagens-leie)
    leie26_m2 = M["leie_2025"] * (1 + M["kpi_nov_2025"]) * 1e6 / M["areal"]
    grid = pd.DataFrame({ey: {ml: resultat(pris, markedsleie=ml, exit_yield=ey)["irr"] for ml in LEIEGRID} for ey in YIELDGRID})
    grid_bud = pd.DataFrame({ey: {ml: resultat(None, markedsleie=ml, exit_yield=ey)["maks_bud"] for ml in LEIEGRID} for ey in YIELDGRID})
    sc = {}
    for navn in SCENARIER:
        r = resultat(pris, **scenario_over(navn, leie26_m2))
        sc[navn] = {"IRR": r["irr"], "IRR belånt": r["irr_belant"], "Maks bud": resultat(None, **scenario_over(navn, leie26_m2))["maks_bud"]}
    return {"R": R, "pris": pris, "maks_bud": base["maks_bud"], "grid": grid, "grid_bud": grid_bud,
            "scenarier": pd.DataFrame(sc).T, "leie26_m2": leie26_m2}


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    X = run(); R = X["R"]
    print(R["cf"].round(3).to_string())
    print(f"maks bud {X['maks_bud']:.1f}  bud {X['pris']:.0f}  IRR {R['irr']:.4f}  belånt {R['irr_belant']:.4f}  "
          f"startyield {R['netto_startyield']:.4f}  kr/m2 {R['pris_m2']:.0f}  exit {R['exit']:.1f}  multippel {R['multippel']:.2f}/{R['multippel_belant']:.2f}  ICR {R['rentedekning_ar1']:.2f}")
    print("leie 2026 per m2", round(X["leie26_m2"]))
    print((X["grid"] * 100).round(2)); print(X["grid_bud"].round(0)); print(X["scenarier"].round(4))
