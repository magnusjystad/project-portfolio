"""Energi- og klimakartlegging av ti næringsbygg i Pareto Eiendomsfellesskap (PEF) og PEF II.

Byggdata: siste energiattest per bygningsdel (Enova), oppvarmet areal og solcelleanlegg (PAIs bærekraftsrapporter 2025).
Vurdering: EU-taksonomien 7.7 (Finans Norges veileder, juni 2026, Vedlegg B) og CRREM 1,5 °C-baner for Norge (V2.05).
Tiltak: kostnad per spart kWh (første år) fra Enovas energitilskuddsordning (Stortinget, Dok. 15:1032 2024–2025, tabell 2);
solceller: NVE «Kostnader for kraftproduksjon» 2026 (store flate tak). Strømpris: spot NO1 2025 (Nord Pool via
hvakosterstrommen.no) + Elvia energiledd + elavgift 2026.

    python src/analyse.py      # skriver data/resultat_*.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"

# --- Bygg ------------------------------------------------------------------------------------------------------------
# Oppvarmet areal og eksisterende solcelleanlegg: PEF/PEF II bærekraftsrapport 2025 (porteføljeoversikt og «Veien til delmålene»).
BYGG = pd.DataFrame([
    # eiendom, fond, kommune, segment (PAI), oppvarmet BRA, byggeår (Enova), CRREM-type, solceller kWp, solproduksjon MWh/år
    ("Hoffsveien 70 B", "PEF II", "Oslo", "Kontor", 7450, 1999, "Office", 72, 58),
    ("Hoffsveien 70 C", "PEF II", "Oslo", "Kontor", 5115, 2000, "Office", 66, 54),
    ("Depotgata 22", "PEF II", "Lillestrøm", "Kontor", 5800, 2014, "Office", 0, 0),
    ("Hotvedtveien 6", "PEF II", "Sandefjord", "Handel", 12487, 2001, "Retail Warehouse", 0, 0),
    ("Toveien 28", "PEF", "Vestby", "Lager", 30440, 2009, "Distribution Warehouse Warm", 5002, 6027),
    ("Nesoddveien 22", "PEF", "Frogn", "Terminal/lager", 5201, 2012, "Distribution Warehouse Warm", 394, 409),
    ("Stolvstadlia 9", "PEF", "Ringsaker", "Lager", 9887, 2008, "Distribution Warehouse Warm", 0, 0),
    ("Industriveien 26", "PEF", "Nittedal", "Lager", 11399, 1984, "Distribution Warehouse Warm", 701, 571),
    ("Karoline Eggens vei 3", "PEF", "Lillestrøm", "Lager", 4401, 1975, "Distribution Warehouse Warm", 0, 0),
    ("Energivegen 2", "PEF II", "Ullensaker", "Salg/verksted", 2320, 2005, "Retail Warehouse", 0, 0),     # bilforretning med verksted
], columns=["Eiendom", "Fond", "Kommune", "Segment", "Oppvarmet BRA (m2)", "Byggeår", "CRREM-type", "Solceller (kWp)", "Solproduksjon (MWh/år)"])

# Hoveddelen av hvert bygg (bygningskategori i energiattesten) etter PAIs segment; den bærer hele arealet i beregningen
HOVED = {"Lager": "Lett industri, verksteder", "Terminal/lager": "Lett industri, verksteder", "Kontor": "Kontorbygg",
         "Handel": "Forretningsbygg", "Salg/verksted": "Forretningsbygg"}

# Taksonomi, topp 15 % (kWh/m²·år), Finans Norges veileder juni 2026, Vedlegg B:
#   ny metode (attest fra 1.1.2026, klimakorrigert vektet levert energi): offisielle terskler 28.4.2026
#   gammel metode (attest før 2026, levert energi ved normalisert klima): NVE/Norconsult 2024, tabell 7-2 «ekskl. NSPEK og klima»
TOPP15 = {("Kontorbygg", "ny"): 125, ("Forretningsbygg", "ny"): 185, ("Lett industri, verksteder", "ny"): 160,
          ("Kontorbygg", "gammel"): 130, ("Forretningsbygg", "gammel"): 185, ("Lett industri, verksteder", "gammel"): 165}

# Enova, energitilskuddsordningen (Stortinget Dok. 15:1032, tabell 2): totale kostnader og spart/produsert kWh første år
ENOVA = pd.DataFrame([
    ("Energistyring og måling (SD-anlegg)", 176_000_000, 16_566_000), ("Energiledelse, styring og måling", 177_000_000, 15_300_000),
    ("LED-belysning med styring", 485_000_000, 32_872_000), ("Behovsstyrt ventilasjon", 124_000_000, 8_183_000),
    ("Ny varmegjenvinner i ventilasjon", 236_000_000, 14_641_000), ("Varmepumpe luft/luft", 120_000_000, 20_660_000),
    ("Varmepumpe luft/vann", 140_000_000, 11_548_000), ("Varmepumpe væske/vann", 255_000_000, 18_407_000),
    ("Etterisolering tak/kaldt loft", 189_000_000, 8_446_000), ("Etterisolering yttervegg", 186_000_000, 8_075_000),
    ("Utskifting vinduer", 360_000_000, 11_025_000), ("Solceller", 1_060_000_000, 68_660_000),
], columns=["Tiltak", "Kostnad (kr)", "kWh første år"]).set_index("Tiltak")
ENOVA["kr per årlig kWh"] = ENOVA["Kostnad (kr)"] / ENOVA["kWh første år"]

# Tiltakspakke per bygg (valgt ut fra bygningstype, alder, energikarakter og om det finnes solceller)
PAKKE = {
    "Depotgata 22": ["Energistyring og måling (SD-anlegg)", "Behovsstyrt ventilasjon", "LED-belysning med styring"],
    "Hotvedtveien 6": ["Energistyring og måling (SD-anlegg)", "LED-belysning med styring", "Varmepumpe luft/vann"],
    "Nesoddveien 22": ["LED-belysning med styring", "Energistyring og måling (SD-anlegg)"],
    "Stolvstadlia 9": ["LED-belysning med styring", "Energistyring og måling (SD-anlegg)", "Varmepumpe luft/luft"],
    "Industriveien 26": ["LED-belysning med styring", "Energistyring og måling (SD-anlegg)", "Varmepumpe luft/luft", "Ny varmegjenvinner i ventilasjon"],
    "Karoline Eggens vei 3": ["LED-belysning med styring", "Energistyring og måling (SD-anlegg)", "Varmepumpe luft/luft", "Etterisolering tak/kaldt loft"],
    "Energivegen 2": ["LED-belysning med styring", "Energistyring og måling (SD-anlegg)", "Behovsstyrt ventilasjon", "Varmepumpe luft/luft"],
}
SOL_NYTT = ["Hotvedtveien 6", "Stolvstadlia 9", "Karoline Eggens vei 3"]     # én-etasjes bygg uten solceller i dag

# Solceller (NVE, lcoe_2026_regneark.xlsx, «Store flate tak»): 7 150 kr/kWp, 760 kWh/kWp, drift 71,5 kr/kW/år
SOL = {"kr/kWp": 7150, "kWh/kWp": 760, "drift kr/kW/år": 71.5}

# Strømpris (øre/kWh eks. mva.): spot NO1 2025 + Elvia energiledd >100 MWh lavspent (fra 1.7.2026) + elavgift 2026
ELVIA_ENERGILEDD, ELAVGIFT = 5.0, 7.13
# Utslippsfaktorer for strøm (g CO2e/kWh): NVE klimadeklarasjon fysisk levert strøm 2025; NS 3720 europeisk miks (scenario 2)
EF = {"NVE 2025 (lokasjonsbasert)": 9.4, "Europeisk miks (NS 3720)": 136.0}


def spotpris():
    s = pd.read_csv(D / "spotpris_NO1_daglig.csv")
    return {"2025": s.loc[s["dato"].str[:4] == "2025", "øre/kWh"].mean(), "2026 hittil": s.loc[s["dato"].str[:4] == "2026", "øre/kWh"].mean()}


def attester():
    """Siste attest per bygg og bygningskategori, med metode (ny fra 2026) og verdien taksonomien skal testes mot."""
    a = pd.read_csv(D / "energiattester_10_bygg.csv", parse_dates=["Utstedt"])
    a = a.sort_values("Utstedt").groupby(["Eiendom", "Bygningskategori"]).tail(1).copy()
    a["Metode"] = np.where(a["Utstedt"] >= "2026-01-01", "ny", "gammel")
    a["Testverdi (kWh/m2)"] = np.where(a["Metode"] == "ny", a["BeregnetVektetLevertEnergiReferanseklimaKWhm2"], a["kWh/m2"])
    a["Topp 15 %-grense"] = [TOPP15[(k, m)] for k, m in zip(a["Bygningskategori"], a["Metode"])]
    a["Energimerke A"] = a["Energikarakter"] == "A"
    a["Under topp 15 %-grensen"] = a["Testverdi (kWh/m2)"] <= a["Topp 15 %-grense"]
    a["Taksonomiforenlig (energikriteriet)"] = a["Energimerke A"] | a["Under topp 15 %-grensen"]
    a["Gyldig til"] = a["Utstedt"] + pd.DateOffset(years=10)
    return a


def bygg_intensitet(a):
    """Én levert-energi-intensitet per bygg (kWh/m², uvektet). Der attestene oppgir areal per del (v2) vektes delene;
    ellers brukes hoveddelen (lager for logistikkbygg, kontor for kontorbygg, forretning for handel)."""
    rows = []
    for e, g in a.groupby("Eiendom"):
        if g["OppvarmetBra"].notna().all() and len(g) > 1:
            v = float(np.average(g["kWh/m2"], weights=g["OppvarmetBra"])); kilde = "arealvektet (v2-attester)"
        else:
            hoved = HOVED[BYGG.set_index("Eiendom").loc[e, "Segment"]]
            v = float(g.loc[g["Bygningskategori"] == hoved, "kWh/m2"].iloc[0]); kilde = f"hoveddel ({hoved})"
        rows.append({"Eiendom": e, "Levert energi (kWh/m2)": v, "Grunnlag": kilde,
                     "Taksonomiforenlig, alle deler": bool(g["Taksonomiforenlig (energikriteriet)"].all()),
                     "Energikarakterer": " / ".join(f"{k.split(',')[0].replace('bygg', '')}: {c}" for k, c in zip(g["Bygningskategori"], g["Energikarakter"]))})
    return pd.DataFrame(rows).set_index("Eiendom")


def crrem():
    c = pd.read_csv(D / "crrem_norge.csv", header=[0, 1], index_col=0, skiprows=[2])
    c.index = c.index.astype(int)
    return c["kWh/m2"], c["kgCO2/m2"]


def crrem_ef():
    """CRREM V2.05 utslippsfaktor for strøm i Norge (kg CO2e/kWh), lokasjonsbasert, interpolert over manglende år."""
    from openpyxl import load_workbook
    wb = load_workbook(D / "kilde" / "crrem_emission_factors_v2.05.xlsx", read_only=True, data_only=True)
    ws = wb["Emission Factors"]
    rows = list(ws.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r and "Country" in [str(x) for x in r if x])
    hdr = rows[hi]
    for r in rows[hi + 1:]:
        if r and "Norway" in [str(x) for x in r if x]:
            ys = {int(h): r[j] for j, h in enumerate(hdr) if isinstance(h, (int, float)) and 2000 < h < 2100 and r[j] is not None}
            s = pd.Series(ys, dtype=float).replace(0, np.nan).interpolate()
            return s
    raise ValueError("fant ikke Norge i CRREM-faktorfilen")


def run():
    a = attester()
    b = BYGG.set_index("Eiendom").join(bygg_intensitet(a))
    eui, co2 = crrem()
    sp = spotpris()
    pris = {k: (v + ELVIA_ENERGILEDD + ELAVGIFT) / 100 for k, v in sp.items()}           # kr/kWh
    b["Energibruk (MWh/år)"] = b["Levert energi (kWh/m2)"] * b["Oppvarmet BRA (m2)"] / 1000
    for k, f in EF.items():
        b[f"Utslipp {k} (tCO2e)"] = b["Energibruk (MWh/år)"] * f / 1000
    for y in (2025, 2030, 2040):
        b[f"CRREM {y} (kWh/m2)"] = [eui.loc[y, t] for t in b["CRREM-type"]]
    years = [int(y) for y in eui.index]
    b["Over CRREM-banen fra"] = [next((y for y in years if eui.loc[y, t] < v), None) for t, v in zip(b["CRREM-type"], b["Levert energi (kWh/m2)"])]
    # Mål: taksonomigrensen for hoveddelen (målt mot samme metode som attesten) og CRREM 2030
    tax_gap = {}
    for e, g in a.groupby("Eiendom"):
        h = g[g["Bygningskategori"] == HOVED[b.loc[e, "Segment"]]].iloc[0]          # hoveddelen bærer arealet i beregningen
        tax_gap[e] = 0.0 if h["Taksonomiforenlig (energikriteriet)"] else float(h["Testverdi (kWh/m2)"] - h["Topp 15 %-grense"])
    b["Reduksjon til taksonomigrensen (kWh/m2)"] = pd.Series(tax_gap)
    b["Reduksjon til CRREM 2030 (kWh/m2)"] = (b["Levert energi (kWh/m2)"] - b["CRREM 2030 (kWh/m2)"]).clip(lower=0)
    b["Mål for reduksjon (kWh/m2)"] = b[["Reduksjon til taksonomigrensen (kWh/m2)", "Reduksjon til CRREM 2030 (kWh/m2)"]].max(axis=1)
    b["Mål for reduksjon (MWh/år)"] = b["Mål for reduksjon (kWh/m2)"] * b["Oppvarmet BRA (m2)"] / 1000
    # CRREM CO2: utslippsintensitet med CRREMs egen netto utslippsfaktor for Norge (V2.05), sammenlignet med CO2-banen
    ef = crrem_ef()
    b["CO2-intensitet 2025, CRREM-faktor (kg/m2)"] = b["Levert energi (kWh/m2)"] * ef.loc[2025]
    b["Over CRREM CO2-banen fra"] = [next((y for y in years if co2.loc[y, t] < v * ef.loc[y]), None) for t, v in zip(b["CRREM-type"], b["Levert energi (kWh/m2)"])]
    # Indikasjon: forholdet mellom vektet (ny metode) og uvektet levert energi i 2026-attestene
    v2 = a[a["Metode"] == "ny"]
    ratio_vekt = (v2["BeregnetVektetLevertEnergiReferanseklimaKWhm2"] / v2["kWh/m2"])
    b["Indikasjon ny metode (kWh/m2, vektet)"] = np.where(b.index.isin(v2["Eiendom"]), np.nan, b["Levert energi (kWh/m2)"] * ratio_vekt.max())
    # Tiltakspakker: nivå 1 = til taksonomigrensen, nivå 2 = videre til CRREM 2030
    rows = []
    for e, pk in PAKKE.items():
        sub = ENOVA.loc[pk]
        unit = sub["Kostnad (kr)"].sum() / sub["kWh første år"].sum()
        for niva, col in [("1: taksonomi (topp 15 %)", "Reduksjon til taksonomigrensen (kWh/m2)"), ("2: CRREM 2030", "Reduksjon til CRREM 2030 (kWh/m2)")]:
            red = b.loc[e, col]
            if niva.startswith("2"):
                red = max(0.0, red - b.loc[e, "Reduksjon til taksonomigrensen (kWh/m2)"])     # i tillegg til nivå 1
            kwh = red * b.loc[e, "Oppvarmet BRA (m2)"]
            if kwh <= 0:
                continue
            rows.append({"Eiendom": e, "Nivå": niva, "Tiltak": "; ".join(pk), "Enhetskostnad (kr per årlig kWh)": unit,
                         "Reduksjon (kWh/m2)": red, "Andel av dagens energibruk": red / b.loc[e, "Levert energi (kWh/m2)"],
                         "Besparelse (MWh/år)": kwh / 1000, "Investering (MNOK)": kwh * unit / 1e6,
                         "Årlig besparelse 2025-pris (MNOK)": kwh * pris["2025"] / 1e6, "Årlig besparelse 2026-pris (MNOK)": kwh * pris["2026 hittil"] / 1e6,
                         "Tilbakebetaling 2025-pris (år)": unit / pris["2025"], "Tilbakebetaling 2026-pris (år)": unit / pris["2026 hittil"],
                         "Tilbakebetaling med 30 % Enova-støtte, 2025-pris (år)": 0.7 * unit / pris["2025"],
                         "Utslippskutt NVE 2025 (tCO2e)": kwh * EF["NVE 2025 (lokasjonsbasert)"] / 1e6,
                         "Utslippskutt europeisk miks (tCO2e)": kwh * EF["Europeisk miks (NS 3720)"] / 1e6})
    T = pd.DataFrame(rows).set_index("Eiendom")
    # Nye solcelleanlegg: kapasitet fra PEF-byggenes median kWp per m² oppvarmet areal (byggene med anlegg)
    ratio = float((BYGG.loc[(BYGG["Solceller (kWp)"] > 0) & BYGG["Segment"].str.contains("Lager"), "Solceller (kWp)"]
                   / BYGG.loc[(BYGG["Solceller (kWp)"] > 0) & BYGG["Segment"].str.contains("Lager"), "Oppvarmet BRA (m2)"]).median())
    srows = []
    for e in SOL_NYTT:
        kwp = ratio * b.loc[e, "Oppvarmet BRA (m2)"]
        prod = kwp * SOL["kWh/kWp"]
        capex = kwp * SOL["kr/kWp"]
        drift = kwp * SOL["drift kr/kW/år"]
        srows.append({"Eiendom": e, "kWp": kwp, "Produksjon (MWh/år)": prod / 1000, "Investering (MNOK)": capex / 1e6,
                      "Netto årlig verdi 2025-pris (MNOK)": (prod * pris["2025"] - drift) / 1e6,
                      "Tilbakebetaling 2025-pris (år)": capex / (prod * pris["2025"] - drift),
                      "Tilbakebetaling 2026-pris (år)": capex / (prod * pris["2026 hittil"] - drift)})
    S = pd.DataFrame(srows).set_index("Eiendom")
    return {"attester": a, "bygg": b, "tiltak": T, "ratio_vekt": ratio_vekt, "sol": S, "pris": pris, "spot": sp, "sol_ratio": ratio, "eui": eui, "co2": co2}


if __name__ == "__main__":
    R = run()
    pd.set_option("display.width", 250)
    cols = ["Bygningskategori", "Energikarakter", "Utstedt", "Metode", "kWh/m2", "Testverdi (kWh/m2)", "Topp 15 %-grense", "Taksonomiforenlig (energikriteriet)"]
    print(R["attester"].set_index("Eiendom")[cols].round(1).to_string())
    print(R["bygg"][["Levert energi (kWh/m2)", "Grunnlag", "Energibruk (MWh/år)", "CRREM 2030 (kWh/m2)", "Over CRREM-banen fra",
                     "Reduksjon til taksonomigrensen (kWh/m2)", "Reduksjon til CRREM 2030 (kWh/m2)", "Mål for reduksjon (MWh/år)"]].round(1).to_string())
    print(R["bygg"][["CO2-intensitet 2025, CRREM-faktor (kg/m2)", "Over CRREM CO2-banen fra", "Indikasjon ny metode (kWh/m2, vektet)"]].round(2).to_string()); print(R["tiltak"].round(2).to_string()); print(R["sol"].round(2).to_string()); print(R["pris"], R["sol_ratio"])
    R["attester"].to_csv(D / "resultat_taksonomi_per_attest.csv", index=False)
    R["bygg"].to_csv(D / "resultat_bygg.csv"); R["tiltak"].to_csv(D / "resultat_tiltak.csv"); R["sol"].to_csv(D / "resultat_solceller.csv")
    ENOVA.to_csv(D / "enova_tiltakskostnader.csv")
