"""Lager report/energi_klima_kartlegging.pdf og figurene fra src/analyse.py.

    python src/lag_rapport.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT.parent), str(ROOT / "src")]
import numpy as np
import pandas as pd

import analyse as A
from common.plotting import PALETTE, setup, source
from common.report import Report

plt = setup()
FIG = ROOT / "report" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
R = A.run()
b, a, T, S = R["bygg"], R["attester"], R["tiltak"], R["sol"]
eui = R["eui"]
cmw = lambda ws: [w * 28.35 for w in ws]
nr = lambda x, d=0: f"{x:,.{d}f}".replace(",", " ").replace(".", ",")
pct = lambda x: f"{x * 100:.0f} %"
p25, p26 = R["pris"]["2025"], R["pris"]["2026 hittil"]
SRC = "Kilde: Enova energimerkeregister; PAI bærekraftsrapporter 2025; Finans Norge (2026); CRREM V2.05; egne beregninger."

# --- Figur 1: energibruk mot taksonomigrense og CRREM 2030 -------------------------------------------------------------
HOVED = A.HOVED
def wrap(e):
    """Bygningsnavn over to linjer på x-aksen, delt ved mellomrommet nærmest midten."""
    i = min((j for j, c in enumerate(e) if c == " "), key=lambda j: abs(j - len(e) / 2))
    return e[:i] + "\n" + e[i + 1:]


hv = []
for e, r in b.iterrows():
    h = a[(a["Eiendom"] == e) & (a["Bygningskategori"] == HOVED[r["Segment"]])].iloc[0]
    hv.append((e, h["Testverdi (kWh/m2)"], h["Topp 15 %-grense"], h["Metode"], h["Energikarakter"]))
hv = pd.DataFrame(hv, columns=["Eiendom", "Testverdi", "Grense", "Metode", "Karakter"]).set_index("Eiendom")
fig, ax = plt.subplots(figsize=(9.5, 4.2))
x = np.arange(len(b))
ax.bar(x - 0.2, b["Levert energi (kWh/m2)"], 0.4, color=PALETTE[0], label="Beregnet levert energi (attest, uvektet)")
ax.bar(x + 0.2, hv["Testverdi"], 0.4, color=PALETTE[2], label="Verdien taksonomien testes mot (vektet ved ny metode)")
ax.scatter(x + 0.2, hv["Grense"], marker="_", s=500, color="#B22222", lw=2.5, label="Topp 15 %-grense", zorder=3)
ax.scatter(x - 0.2, b["CRREM 2030 (kWh/m2)"], marker="_", s=500, color="black", lw=2.5, label="CRREM-banen 2030", zorder=3)
for i, (e, r) in enumerate(hv.iterrows()):
    ax.text(i, max(b.loc[e, "Levert energi (kWh/m2)"], r["Testverdi"]) + 8, r["Karakter"], ha="center", fontsize=8, fontweight="bold")
ax.set_xticks(x, [wrap(e) for e in b.index], fontsize=7)
ax.set_ylabel("kWh/m² per år"); ax.legend(fontsize=7.5, loc="upper left")
ax.set_title("Hoveddelen av hvert bygg mot taksonomigrensen og CRREM 2030 (bokstav = energikarakter)")
source(ax, SRC)
fig.savefig(FIG / "fig_bygg_mot_grenser.png"); plt.close(fig)

# --- Figur 2: CRREM-baner -------------------------------------------------------------------------------------------------
fig, axs = plt.subplots(1, 2, figsize=(10, 3.8))
for ax, typ, tit in [(axs[0], "Office", "Kontor"), (axs[1], "Distribution Warehouse Warm", "Lager/logistikk (oppvarmet)")]:
    yrs = eui.index.astype(int)
    ax.plot(yrs, eui[typ], color="black", lw=2, label="CRREM 1,5 °C, Norge")
    sel = b[b["CRREM-type"] == typ]
    for i, (e, r) in enumerate(sel.iterrows()):
        ax.scatter([2025], [r["Levert energi (kWh/m2)"]], color=PALETTE[i % len(PALETTE)], s=40, zorder=3, label=e)
    if typ == "Distribution Warehouse Warm":
        ax.axhline(94, color="grey", ls=":", lw=1.2); ax.text(2036, 98, "PEF målt snitt 2025: 94 kWh/m²", fontsize=7, color="grey")
    else:
        ax.axhline(121, color="grey", ls=":", lw=1.2); ax.text(2033, 125, "PEF II målt snitt 2025: 121 kWh/m²", fontsize=7, color="grey")
    ax.set_title(tit, fontsize=10); ax.set_ylabel("kWh/m² per år"); ax.legend(fontsize=6.5, loc="upper right")
source(axs[0], "Kilde: CRREM V2.05 (www.crrem.org); Enova; PAI bærekraftsrapporter 2025.")
fig.tight_layout(); fig.savefig(FIG / "fig_crrem.png"); plt.close(fig)

# --- Figur 3: tiltak, investering og tilbakebetaling ---------------------------------------------------------------------
t1 = T[T["Nivå"].str.startswith("1")]
items = [(f"{wrap(e)}\n(effektivisering)", r["Investering (MNOK)"], r["Tilbakebetaling 2025-pris (år)"], r["Tilbakebetaling 2026-pris (år)"]) for e, r in t1.iterrows()]
items += [(f"{wrap(e)}\n(solceller)", r["Investering (MNOK)"], r["Tilbakebetaling 2025-pris (år)"], r["Tilbakebetaling 2026-pris (år)"]) for e, r in S.iterrows()]
fig, ax = plt.subplots(figsize=(9.5, 3.9))
x = np.arange(len(items))
ax.bar(x - 0.2, [i[2] for i in items], 0.4, color=PALETTE[0], label="Tilbakebetaling, 2025-pris (år)")
ax.bar(x + 0.2, [i[3] for i in items], 0.4, color=PALETTE[1], label="Tilbakebetaling, 2026-pris (år)")
for i, it in enumerate(items):
    ax.text(i, max(it[2], it[3]) + 0.4, f"NOK {nr(it[1], 1)} mill.", ha="center", fontsize=7)
ax.set_xticks(x, [i[0] for i in items], fontsize=6.6); ax.set_ylabel("år"); ax.legend(fontsize=8, loc="upper right"); ax.set_ylim(0, 21)
ax.set_title("Nivå 1-tiltak og nye solcelleanlegg: investering og enkel tilbakebetalingstid")
ax.set_xlabel(" ")
source(ax, "Kilde: Enova (Stortinget Dok. 15:1032, tabell 2); NVE kostnader for kraftproduksjon 2026; Nord Pool NO1; Elvia; Skatteetaten.")
fig.savefig(FIG / "fig_tiltak.png"); plt.close(fig)

# --- Rapport -------------------------------------------------------------------------------------------------------------
tax_ok = b["Taksonomiforenlig, alle deler"]
area = b["Oppvarmet BRA (m2)"]
ORD = {2: "to", 3: "tre", 4: "fire", 5: "fem", 6: "seks", 7: "sju", 8: "åtte", 9: "ni", 10: "ti"}
n_bygg, n_ute = len(b), int((~tax_ok).sum())
ny_bygg = sorted(set(a.loc[a["Metode"] == "ny", "Eiendom"]))
gammel_ute = [e for e in b.index if e not in ny_bygg and not tax_ok[e]]
rv = R["ratio_vekt"]
spenn = lambda s, d=0: f"{nr(s.min(), d)}–{nr(s.max(), d)}"
lager = T[b.loc[T.index, "CRREM-type"].str.startswith("Distribution").values].groupby(level=0)["Andel av dagens energibruk"].sum()
tot_mwh = b["Energibruk (MWh/år)"].sum()
lvl1 = t1[["Besparelse (MWh/år)", "Investering (MNOK)", "Årlig besparelse 2025-pris (MNOK)"]].sum()
lvl2 = T[["Besparelse (MWh/år)", "Investering (MNOK)"]].sum()
r = Report(ROOT / "report" / "energi_klima_kartlegging.pdf", f"Energi- og klimakartlegging av {ORD[n_bygg]} næringsbygg",
           "Investment Research Portfolio · Prosjekt 18 · bygg i Pareto Eiendomsfellesskap (PEF) og PEF II · oktober 2026")
r.h1("Sammendrag")
r.abstract(
    f"{ORD[n_bygg].capitalize()} bygg på til sammen {nr(area.sum())} kvm oppvarmet areal er kartlagt: kontor, handel og logistikk. Grunnlaget er Enovas "
    f"energiattester og PAIs bærekraftsrapporter. Byggene bruker beregnet {nr(tot_mwh / 1000, 1)} GWh i året. Med NVEs utslippsfaktor for "
    f"2025 (9,4 g/kWh) gir det {nr(b['Utslipp NVE 2025 (lokasjonsbasert) (tCO2e)'].sum())} tonn CO₂e. Med europeisk strømmiks (136 g/kWh) "
    f"er tallet {nr(b['Utslipp Europeisk miks (NS 3720) (tCO2e)'].sum())} tonn. <b>EU-taksonomien:</b> {int(tax_ok.sum())} av {n_bygg} bygg "
    f"({pct(area[tax_ok].sum() / area.sum())} av arealet) oppfyller energikriteriet, enten med energimerke A eller ved å ligge blant de 15 % "
    f"beste. Alle som har fått ny attest i 2026 er innenfor. <b>CRREM:</b> kontorbyggene ligger under banen til 2040-tallet, mens "
    f"logistikkbyggene med beregnede tall over 180 kWh/m² allerede ligger over den strenge logistikkbanen (66 kWh/m² i 2030). "
    f"<b>Tiltaksplan:</b> for å få de {ORD[n_ute]} byggene utenfor taksonomien under grensen trengs det om lag {nr(lvl1['Besparelse (MWh/år)'])} MWh "
    f"spart per år. Med Enovas faktiske kostnad per spart kWh koster det NOK {nr(lvl1['Investering (MNOK)'], 1)} mill. Tilbakebetalingstiden "
    f"er {spenn(t1['Tilbakebetaling 2025-pris (år)'])} år med 2025-pris og {spenn(t1['Tilbakebetaling 2026-pris (år)'])} år med 2026-pris. "
    f"Nye solcelleanlegg på {ORD[len(S)]} tak gir {spenn(pd.concat([S['Tilbakebetaling 2026-pris (år)'], S['Tilbakebetaling 2025-pris (år)']]))} år. <b>Det billigste første steget er "
    f"en ny energiattest etter ny metode</b> for de {ORD[len(gammel_ute)]} byggene utenfor med eldre attest, fordi den vektede metoden ga {(1 - rv.max()) * 100:.0f}–{pct(1 - rv.min())} lavere tall i "
    f"2026-attestene.")

r.h1("1. Byggene og datagrunnlaget")
bt = pd.DataFrame({
    "Eiendom": b.index, "Fond": b["Fond"], "Type": b["Segment"], "Oppv. areal (m²)": [nr(v) for v in area],
    "Energikarakterer": b["Energikarakterer"], "Levert energi (kWh/m²)": [nr(v) for v in b["Levert energi (kWh/m2)"]],
    "MWh/år": [nr(v) for v in b["Energibruk (MWh/år)"]], "Solceller i dag (kWp)": [nr(v) for v in b["Solceller (kWp)"]]})
r.table(bt, caption="Tabell 1. Byggene. Energikarakter og levert energi er fra siste energiattest per bygningsdel (Enova). For bygg med flere "
        "deler brukes hoveddelen, eller arealvektet snitt der attesten oppgir areal per del. Oppvarmet areal og solceller er fra PAIs "
        "bærekraftsrapporter for 2025. Eierselskapenes organisasjonsnummer på attestene er sjekket mot Enhetsregisteret.",
        index=False, col_widths=cmw([3.4, 1.4, 2.2, 1.8, 3.6, 1.8, 1.4, 1.6]), font=6.9)
r.p(f"<b>Beregnet og målt energibruk.</b> Energiattesten viser beregnet levert energi ved normert bruk og klima, ikke det byggene faktisk "
    f"bruker. Målt energibruk er bare offentlig på porteføljenivå: 94 kWh/m² i PEF og 121 kWh/m² i PEF II i 2025, før fratrekk for egen "
    f"solkraft. De {ORD[n_bygg]} byggene her har et arealvektet beregnet snitt på {nr(tot_mwh / area.sum() * 1000)} kWh/m². For logistikkbygg er "
    f"normert bruk trolig høyere enn faktisk bruk, fordi lagre ofte holdes kaldere og har kortere driftstid enn standarden forutsetter.")

r.h1("2. EU-taksonomien (aktivitet 7.7, kjøp og eie av bygg)")
r.p("For bygg oppført før 2021 er kriteriet energimerke A, eller å ligge blant de 15 % beste i den nasjonale bygningsmassen. Grensene og "
    "metoden følger Finans Norges veileder fra juni 2026 (Vedlegg B):")
r.bullets([
    "Attester utstedt fra 1. januar 2026 (ny metode) testes på klimakorrigert vektet levert energi mot de offisielle grensene fra 28.4.2026: "
    "kontor 125, forretning 185 og lett industri/lager 160 kWh/m².",
    "Eldre attester testes på levert energi ved normalisert klima mot NVE/Norconsults grenser «ekskl. NSPEK og klima»: kontor 130, "
    "forretning 185 og lager 165 kWh/m².",
])
at = a.sort_values(["Eiendom", "Bygningskategori"])
att = pd.DataFrame({"Eiendom": at["Eiendom"], "Del": at["Bygningskategori"].str.replace(", verksteder", ""), "Karakter": at["Energikarakter"],
                    "Utstedt": at["Utstedt"].dt.strftime("%m.%Y"), "Metode": at["Metode"], "Testverdi": [nr(v, 1) for v in at["Testverdi (kWh/m2)"]],
                    "Grense": at["Topp 15 %-grense"].astype(int), "Forenlig": np.where(at["Taksonomiforenlig (energikriteriet)"], "ja", "nei"),
                    "Gyldig til": at["Gyldig til"].dt.strftime("%m.%Y")})
r.table(att, caption="Tabell 2. Taksonomitest per bygningsdel. Testverdien er vektet levert energi for attester etter ny metode, ellers levert "
        "energi (kWh/m² per år).", index=False, col_widths=cmw([3.3, 2.6, 1.4, 1.5, 1.4, 1.5, 1.3, 1.4, 1.6]), font=7.2)
r.p(f"Alle de {ORD[len(ny_bygg)]} byggene med attest fra 2026 er forenlige, enten med energimerke A eller under grensen med god margin. I disse attestene er "
    f"vektet energi {(1 - rv.max()) * 100:.0f}–{pct(1 - rv.min())} lavere enn uvektet. Bruker man det største forholdstallet ({nr(rv.max(), 2)}) på "
    f"byggene med eldre attest, havner Hotvedtveien 6 (≈{nr(b.loc['Hotvedtveien 6', 'Indikasjon ny metode (kWh/m2, vektet)'])}), Stolvstadlia 9 "
    f"(≈{nr(b.loc['Stolvstadlia 9', 'Indikasjon ny metode (kWh/m2, vektet)'])}) og Industriveien 26 (≈{nr(b.loc['Industriveien 26', 'Indikasjon ny metode (kWh/m2, vektet)'])}) "
    f"under grensene sine. Karoline Eggens vei 3 (≈{nr(b.loc['Karoline Eggens vei 3', 'Indikasjon ny metode (kWh/m2, vektet)'])}, grense 160) og "
    f"Energivegen 2 (≈{nr(b.loc['Energivegen 2', 'Indikasjon ny metode (kWh/m2, vektet)'])}, grense 185) gjør det ikke. "
    "Dette er bare en indikasjon. Vektingen avhenger av energibærere og teknisk løsning, så en ny attest må bekrefte det.")
r.image(FIG / "fig_bygg_mot_grenser.png", 16.0, "Figur 1. Hoveddelen av hvert bygg mot taksonomigrensen og CRREM-banen for 2030.")

r.h1("3. CRREM-nedtrappingsbanen")
cr = pd.DataFrame({"Eiendom": b.index, "CRREM-type": b["CRREM-type"], "Levert energi": [nr(v) for v in b["Levert energi (kWh/m2)"]],
                   "CRREM 2025 / 2030 / 2040": [f"{nr(x)} / {nr(y)} / {nr(z)}" for x, y, z in zip(b["CRREM 2025 (kWh/m2)"], b["CRREM 2030 (kWh/m2)"], b["CRREM 2040 (kWh/m2)"])],
                   "Over energibanen fra": [("før 2020" if v == 2020 else str(int(v))) if pd.notna(v) else "etter 2050" for v in b["Over CRREM-banen fra"]],
                   "kg CO₂/m² (CRREM-faktor)": [nr(v, 2) for v in b["CO2-intensitet 2025, CRREM-faktor (kg/m2)"]],
                   "Over CO₂-banen fra": [str(int(v)) if pd.notna(v) else "etter 2050" for v in b["Over CRREM CO2-banen fra"]]})
r.table(cr, caption="Tabell 3. Byggene mot CRREM 1,5 °C-banene for Norge (V2.05). Energiintensitet i kWh/m² per år. CO₂-intensiteten bruker "
        "CRREMs utslippsfaktor for norsk strøm (6,7 g/kWh i 2025, synkende mot null i 2050).", index=False,
        col_widths=cmw([3.4, 4.0, 1.6, 3.0, 1.9, 2.0, 1.8]), font=7.0)
r.image(FIG / "fig_crrem.png", 16.0, "Figur 2. CRREM-banene for kontor og oppvarmet lager, med byggenes beregnede energibruk og PAIs målte "
        "porteføljesnitt.")
r.p("CRREM skal brukes på målt energibruk. Med beregnede tall fra attestene ligger alle logistikkbyggene unntatt Toveien 28 allerede over "
    "logistikkbanen. Men PEFs målte snitt (94 kWh/m²) ligger også over banen for 2025 (81). Logistikkbanen i CRREM er altså svært krevende "
    "for norske lagerbygg, uansett om tallene er beregnede eller målte. Målt mot CO₂-banen er bildet annerledes. Med norsk strøm ligger "
    "byggene under banen i mange år, og bare Karoline Eggens vei 3 ligger over allerede nå. Det viser at energibruk, ikke utslipp, er "
    "hovedrisikoen for norske bygg i CRREM.")

r.h1("4. Tiltaksplan, kostnad og tilbakebetaling")
r.p(f"<b>Metode.</b> Tiltakspakken er valgt ut fra byggtype, alder og dagens løsning. Kostnaden settes ved å gange nødvendig energikutt med "
    f"Enovas faktiske kostnad per spart kWh første år, for de samme tiltakene i energitilskuddsordningen (3 912 tiltak, tabell 2 i "
    f"Stortinget Dok. 15:1032). Strømprisen er spot i NO1 for 2025 ({nr(R['spot']['2025'], 1)} øre/kWh) pluss Elvias energiledd og elavgift, "
    f"altså {nr(p25 * 100, 1)} øre/kWh eksklusiv mva. Med 2026-prisen så langt ({nr(R['spot']['2026 hittil'], 1)} øre/kWh spot) blir det "
    f"{nr(p26 * 100, 1)} øre/kWh. Effektledd og eventuell Enova-støtte er ikke regnet med i hovedtallene.")
tt = T.copy()
tp = pd.DataFrame({"Eiendom": tt.index, "Nivå": tt["Nivå"].str[:1], "Tiltak": tt["Tiltak"].str.replace("; ", ", "),
                   "Kutt (kWh/m²)": [nr(v) for v in tt["Reduksjon (kWh/m2)"]], "Andel": [pct(v) for v in tt["Andel av dagens energibruk"]],
                   "MWh/år": [nr(v) for v in tt["Besparelse (MWh/år)"]], "MNOK": [nr(v, 1) for v in tt["Investering (MNOK)"]],
                   "Tilb. 2025 / 2026 (år)": [f"{nr(x, 1)} / {nr(y, 1)}" for x, y in zip(tt["Tilbakebetaling 2025-pris (år)"], tt["Tilbakebetaling 2026-pris (år)"])]})
r.table(tp, caption="Tabell 4. Tiltaksplan. Nivå 1 tar bygget under taksonomigrensen. Nivå 2 tar det videre ned til CRREM-banen for 2030 "
        "(kommer i tillegg til nivå 1). Enkel tilbakebetaling = kostnad per årlig kWh / strømpris.", index=False,
        col_widths=cmw([3.0, 0.9, 6.6, 1.4, 1.1, 1.3, 1.2, 2.2]), font=6.8)
st = pd.DataFrame({"Eiendom": S.index, "kWp": [nr(v) for v in S["kWp"]], "MWh/år": [nr(v) for v in S["Produksjon (MWh/år)"]],
                   "Investering (MNOK)": [nr(v, 1) for v in S["Investering (MNOK)"]],
                   "Tilb. 2025 / 2026 (år)": [f"{nr(x, 1)} / {nr(y, 1)}" for x, y in zip(S["Tilbakebetaling 2025-pris (år)"], S["Tilbakebetaling 2026-pris (år)"])]})
r.table(st, caption=f"Tabell 5. Nye solcelleanlegg. Kapasiteten er skalert med PEF-lagrenes median på {R['sol_ratio']:.3f} kWp per m² oppvarmet "
        "areal. Kostnad, ytelse og drift følger NVE 2026 for store flate tak: 7 150 kr/kWp, 760 kWh/kWp og 71,5 kr/kW per år. "
        "All produksjon er verdsatt til innkjøpspris.", index=False, col_widths=cmw([4.0, 2.0, 2.0, 2.6, 3.0]), font=7.5)
r.image(FIG / "fig_tiltak.png", 15.5, "Figur 3. Investering og tilbakebetalingstid for nivå 1-tiltakene og nye solcelleanlegg.")
r.bullets([
    f"<b>Nivå 1 (taksonomi):</b> {nr(lvl1['Besparelse (MWh/år)'])} MWh/år, NOK {nr(lvl1['Investering (MNOK)'], 1)} mill. og NOK "
    f"{nr(lvl1['Årlig besparelse 2025-pris (MNOK)'], 2)} mill. spart per år med 2025-pris. Med 30 % Enova-støtte, som Hoffsveien 70 B/C fikk, "
    f"går tilbakebetalingen ned til {spenn(t1['Tilbakebetaling med 30 % Enova-støtte, 2025-pris (år)'])} år.",
    f"<b>Nivå 1 og 2 (CRREM 2030):</b> {nr(lvl2['Besparelse (MWh/år)'])} MWh/år og NOK {nr(lvl2['Investering (MNOK)'], 1)} mill. Kuttene "
    f"tilsvarer {lager.min() * 100:.0f}–{pct(lager.max())} av beregnet bruk i logistikkbyggene med tiltak. Det er mer enn en vanlig tiltakspakke gir, så nivå 2 bør først vurderes mot "
    f"målt forbruk.",
    "<b>Rekkefølge:</b> først ny energiattest etter ny metode og måling per bygg. Deretter SD-anlegg og energiledelse, som har lavest kostnad "
    "per kWh (11–12 kr). Så LED og varmepumper, og til slutt etterisolering og vinduer, som er dyrest (22–33 kr per kWh).",
    f"<b>Klimaavtrykk:</b> nivå 1 kutter {nr(t1['Utslippskutt NVE 2025 (tCO2e)'].sum())} tonn CO₂e i året med norsk faktor, eller "
    f"{nr(t1['Utslippskutt europeisk miks (tCO2e)'].sum())} tonn med europeisk miks. Den økonomiske gevinsten ligger i lavere strømkostnad, "
    f"taksonomiforenlighet og lavere CRREM-risiko, ikke i utslippene alene.",
])

r.h1("5. Begrensninger")
r.bullets([
    "Energibruken er beregnet (energiattest), ikke målt. Målt forbruk per bygg er ikke offentlig.",
    "For fire logistikkbygg med kontordel er arealfordelingen ukjent, så hele arealet regnes med lagerdelens intensitet. Det samme gjelder "
    "Energivegen 2 (bilforretning med verksted), der hele arealet regnes som salgsdelen. De andre delene er vist for seg i tabell 2.",
    "Kostnadene er gjennomsnitt for tiltak som fikk Enova-støtte. Enova støtter prosjekter som ikke er lønnsomme nok alene, så "
    "gjennomsnittet kan være høyere enn for typiske tiltak. Tallene er per kWh spart første år, ikke over levetiden, og tilbakebetalingen "
    "er enkel og udiskontert.",
    "Effektbesparelser (Elvias effektledd), vedlikeholdsgevinster og verdieffekter er ikke regnet med. Det gjør tilbakebetalingen konservativ.",
    "Taksonomien krever også DNSH, inkludert en klimarisikovurdering, og minimumsgarantier. Her vurderes bare energikriteriet.",
    f"Indikasjonen for ny metode bygger på {len(rv)} attester fra 2026 og er usikker.",
])
r.p("<b>Kilder.</b> Enova, Energimerkesystemet – offentlige data (API, data.enova.no). PAI, bærekraftsrapporter 2025 for PEF og PEF II "
    "(paretoai.no). Finans Norge, «Veileder for vurdering av taksonomiforenlig eiendom», juni 2026. NVE/Norconsult, «Forslag til ny "
    "energimerkeskala og terskelverdier», 2024. CRREM Pathways og Emission Factors V2.05 (www.crrem.org). Stortinget Dok. 15:1032 "
    "(2024–2025), svar fra energiministeren med Enova-tall. NVE, «Kostnader for kraftproduksjon» 2026. NVE, strømdeklarasjoner 2025. "
    "Nord Pool day-ahead NO1 via hvakosterstrommen.no. Elvia, nettleie for store bedrifter fra 1.7.2026. Skatteetaten, elavgift 2026. "
    "Brønnøysundregistrene.")
print("sider:", r.build())
