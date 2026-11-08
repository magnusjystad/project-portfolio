"""Lager figurer og investeringsmemoet report/investeringsmemo_fugleasen7.pdf fra Python-modellen (src/modell.py).
Tallene er de samme som i Excel-modellen (kontrollert av src/sjekk_modell.py).

    python src/lag_memo.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent)); sys.path.insert(0, str(ROOT / "src"))
from common.plotting import PALETTE, setup, source  # noqa: E402
from common.report import Report  # noqa: E402
import modell as Mo  # noqa: E402

plt = setup()
D, FIG = ROOT / "data", ROOT / "report" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
nr = lambda x, d=0: f"{x:,.{d}f}".replace(",", " ").replace(".", ",")
pct = lambda x, d=1: f"{x * 100:.{d}f} %".replace(".", ",")
cmw = lambda ws: [w * 28.35 for w in ws]

X = Mo.run(); R = X["R"]; M = Mo.M; A = Mo.ANTAGELSER
cf = R["cf"]
nlp = pd.read_csv(D / "leietaker_regnskap.csv", index_col=0)
f7 = pd.read_csv(D / "fugleasen7_as_regnskap.csv", index_col=0)
tr = pd.read_csv(D / "transaksjoner.csv")
ml = pd.read_csv(D / "markedsleie_omrader.csv")
sc = X["scenarier"]

# Leietakers nøkkeltall
leie = f7["Driftsinntekter"]
NT = pd.DataFrame({
    "Driftsinntekter (mill.)": nlp["Driftsinntekter"], "Omsetningsvekst": nlp["Driftsinntekter"].pct_change(),
    "Driftsmargin": nlp["Driftsresultat"] / nlp["Driftsinntekter"], "Egenkapitalandel": nlp["Egenkapital"] / nlp["Sum eiendeler"],
    "Likviditetsgrad 1": nlp["Omløpsmidler"] / nlp["Kortsiktig gjeld"], "Rentedekning": nlp["Driftsresultat"] / nlp["Finanskostnader"],
    "Leie / driftsinntekter": leie / nlp["Driftsinntekter"], "Leiedekning": (nlp["Driftsresultat"] + leie) / leie,
    "Kontanter / årlig leie": nlp["Bankinnskudd og kontanter"] / leie})

# --- Figur 1: markedsleie per område og Fugleåsen 7 ------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9.5, 4.3))
m = ml.sort_values("Høy (NOK/m2)")
y = np.arange(len(m))
ax.barh(y, m["Høy (NOK/m2)"] - m["Lav (NOK/m2)"], left=m["Lav (NOK/m2)"], color=[PALETTE[1] if o == "Langhus" else PALETTE[0] for o in m["Område"]], height=0.6)
ax.set_yticks(y, m["Område"], fontsize=8)
ax.axvline(X["leie26_m2"], color="#B22222", lw=2, label=f"Fugleåsen 7, kontraktsleie 2026: {nr(X['leie26_m2'])} kr/m²")
ax.axvline(M["pef_leie_snitt"], color="grey", ls="--", lw=1.2, label=f"PEF-porteføljen, snitt: {nr(M['pef_leie_snitt'])} kr/m²")
ax.set_xlabel("NOK per m² per år"); ax.legend(fontsize=8, loc="lower right")
ax.set_title("Markedsleie for lager og logistikk per område (intervall), høsten 2026")
source(ax, "Kilde: Akershus Eiendom, Halvårsrapport høst 2026; Regnskapsregisteret (Fugleåsen 7 AS); PEF Q3 2026.")
fig.savefig(FIG / "fig_markedsleie.png"); plt.close(fig)

# --- Figur 2: kontantstrøm ------------------------------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9.5, 3.9))
yrs = cf.index[:-1]
ax.bar(yrs, cf.loc[yrs, "Netto driftsinntekt"], color=PALETTE[0], label="Netto driftsinntekt (NOI)")
ax.plot(yrs, cf.loc[yrs, "Kontraktsleie (100 %)"] * (1 - A["eierkost"]), color="#B22222", ls="--", lw=1.5, label="NOI om NLP-leien hadde fortsatt")
for x_, v in zip(yrs, cf.loc[yrs, "Netto driftsinntekt"]):
    ax.text(x_, v + 0.6, nr(v, 1), ha="center", fontsize=7.5)
ax.annotate("NLP-kontrakten utløper 30.9.2033;\n6 mnd ledighet og utleiekostnad", xy=(2033, 18.8), xytext=(2031.3, 30),
            fontsize=8, arrowprops=dict(arrowstyle="->", color="grey"))
ax.set_ylabel("NOK mill."); ax.set_xticks(yrs); ax.set_ylim(0, 42); ax.legend(fontsize=8, loc="upper left")
ax.set_title(f"Netto driftsinntekt 2027–2036, basis (markedsleie {nr(A['markedsleie'])} kr/m² i 2026-kroner)")
source(ax, "Kilde: egen modell; leie fra Regnskapsregisteret, KPI fra Norges Bank PPR 3/2026, markedsleie fra Akershus Eiendom.")
fig.savefig(FIG / "fig_kontantstrom.png"); plt.close(fig)

# --- Figur 3: sensitivitet ----------------------------------------------------------------------------------------------
g = X["grid"]
fig, ax = plt.subplots(figsize=(8.5, 4.1))
im = ax.imshow(g.values * 100, cmap="RdYlGn", vmin=4, vmax=11, aspect="auto")
ax.set_xticks(range(len(g.columns)), [pct(c, 2) for c in g.columns], fontsize=8)
ax.set_yticks(range(len(g.index)), [nr(i) for i in g.index], fontsize=8)
for i in range(g.shape[0]):
    for j in range(g.shape[1]):
        v = g.values[i, j]
        bold = g.index[i] == A["markedsleie"] and abs(g.columns[j] - A["exit_yield"]) < 1e-9
        ax.text(j, i, pct(v), ha="center", va="center", fontsize=8, weight="bold" if bold else "normal",
                color="black")
ax.set_xlabel("Exit-yield (netto)"); ax.set_ylabel("Markedsleie ved reutleie (kr/m², 2026-kr)")
ax.set_title(f"Ufinansiert IRR ved kjøpesum NOK {nr(X['pris'])} mill.")
ax.grid(False)
source(ax, "Kilde: egen modell. Fet skrift = basis.")
fig.savefig(FIG / "fig_sensitivitet.png"); plt.close(fig)

# --- Figur 4: transaksjoner, kr per m² ----------------------------------------------------------------------------------
t = tr.dropna(subset=["Pris (NOK mill.)"]).copy()
t["kr/m2"] = t["Pris (NOK mill.)"] * 1e6 / t["Areal (m2)"]
t["navn"] = [f"{k} ({str(d)[:4]})" for k, d in zip(["KLP: Project Athena", "KLP: Urban Partners-porteføljen", "Niam: Ahlsell, Eidsvoll", "Slate: World Seafood Center"], t["Dato"])]
fig, ax = plt.subplots(figsize=(9.5, 3.4))
navn = list(t["navn"]) + ["Fugleåsen 7 ved budet"]
vals = list(t["kr/m2"]) + [R["pris_m2"]]
ax.barh(range(len(navn)), vals, color=[PALETTE[0]] * len(t) + [PALETTE[1]], height=0.6)
for i, v in enumerate(vals):
    ax.text(v + 250, i, nr(v), va="center", fontsize=8)
ax.set_yticks(range(len(navn)), navn, fontsize=8); ax.invert_yaxis(); ax.set_xlim(0, 27000)
ax.set_xlabel("NOK per m²"); ax.set_title("Pris per m² i sammenlignbare transaksjoner og budet på Fugleåsen 7")
source(ax, "Kilde: MT Logistikk; KLP/NTB; Colliers; Wästbygg; Logistikk Inside; egne beregninger (pris / areal).")
fig.savefig(FIG / "fig_transaksjoner.png"); plt.close(fig)

if __name__ == "__main__":
    r = Report(ROOT / "report" / "investeringsmemo_fugleasen7.pdf", "Investeringsmemo: Fugleåsen 7, Langhus",
               "Investment Research Portfolio · Prosjekt 19 · lager/logistikk, Nordre Follo · oktober 2026")
    rev = 1 - X["scenarier"].loc["NLP fornyer til dagens leie", "Maks bud"] / X["maks_bud"]
    r.h1("Anbefaling")
    r.abstract(
        f"<b>Vi anbefaler et bud på NOK {nr(X['pris'])} mill.</b> for Fugleåsen 7: {nr(M['areal'])} m² lager og logistikk på Langhus, "
        f"utleid til Norsk Lastbærer Pool AS (NLP) til trolig september 2033. Budet tilsvarer {nr(R['pris_m2'])} kr/m² og en netto "
        f"startyield på {pct(R['netto_startyield'], 2)}. I basis gir det en ufinansiert IRR på {pct(R['irr'])} over ti år og "
        f"{pct(R['irr_belant'])} med {pct(A['ltv'], 0)} belåning, mot et avkastningskrav på {pct(A['krav'])}. "
        f"Caset hviler på at leien er lav: NLP betaler om lag {nr(X['leie26_m2'])} kr/m², mens markedsleien på Langhus er "
        f"{nr(M['markedsleie_langhus_lav'])}–{nr(M['markedsleie_langhus_hoy'])} kr/m². Om lag {pct(rev, 0)} av verdien kommer fra at "
        f"leien kan heves ved utløp. Derfor byr vi ut fra nedre del av intervallet, ikke midtpunktet (maks pris i basis er NOK "
        f"{nr(X['maks_bud'])} mill.). <b>Største risiko:</b> NLP fornyer til dagens leie. Da faller IRR til "
        f"{pct(sc.loc['NLP fornyer til dagens leie', 'IRR'])}. <b>Motparten er solid:</b> NLP har {nr(nlp.loc[2025, 'Driftsinntekter'])} mill. "
        f"kr i omsetning, {pct(NT.loc[2025, 'Egenkapitalandel'], 0)} egenkapitalandel, og leien utgjør {pct(NT.loc[2025, 'Leie / driftsinntekter'])} "
        f"av omsetningen.")

    r.h1("1. Eiendommen og leieforholdet")
    r.bullets([
        f"<b>Bygget:</b> {nr(M['areal'])} m² driftsstasjon og mellomlager i Fugleåsen næringspark på Langhus, ferdig oktober 2013. "
        "Energimerke A (lager) og B (kontor). Eies i dag av PEF gjennom Fugleåsen 7 AS og utgjorde 4 % av PEFs eiendeler i 2025.",
        "<b>Leieavtalen:</b> NLP inngikk i 2012 en 20-årig avtale med Bulk Eiendom om et nybygg på ca. 21 000 m², i drift fra oktober 2013. "
        "Det gir utløp rundt 30.9.2033. Faktisk startdato, opsjoner og indeksering er ikke offentlige.",
        f"<b>Leien:</b> eierselskapet hadde {nr(leie.loc[2025], 2)} mill. kr i driftsinntekter i 2025 ({nr(leie.loc[2025] * 1e6 / M['areal'])} kr/m²). "
        f"Med KPI-regulering på 3,0 % blir det {nr(X['leie26_m2'])} kr/m² i 2026. Det er {pct(1 - X['leie26_m2'] / M['pef_leie_snitt'], 0)} under PEF-porteføljens snitt "
        f"({nr(M['pef_leie_snitt'])} kr/m²).",
        "<b>Kjøpet:</b> vi forutsetter kjøp av aksjene i eierselskapet med oppgjør 31.12.2026 og salg etter ti år.",
    ])

    r.h1("2. Markedsleie og sammenlignbare transaksjoner")
    r.image(FIG / "fig_markedsleie.png", 15.5, "Figur 1. NLP betaler under nedre del av markedsleien på Langhus.")
    r.p(f"Akershus Eiendom oppgir {nr(M['markedsleie_langhus_lav'])}–{nr(M['markedsleie_langhus_hoy'])} kr/m² for Langhus og «rundt NOK 1 700» "
        f"i etablerte parker som Berger og Langhus. DNB Næringsmegling oppgir et snitt på {nr(M['snittleie_arealstatistikk'])} kr/m² for lager "
        f"(Arealstatistikk). Prime yield er {pct(M['prime_yield_ae'], 2)} (Akershus Eiendom), {pct(M['prime_yield_dnb'], 2)} (DNB) og "
        f"{pct(M['prime_yield_catella'], 2)} (Catella). PEFs egen portefølje er verdsatt til {pct(M['pef_netto_yield'])} netto yield, med "
        f"vektet leietid på 7,3 år. Det bruker vi som exit-yield.")
    tt = tr.copy()
    tt["kr/m²"] = [nr(p * 1e6 / a) if pd.notna(p) else "–" for p, a in zip(tt["Pris (NOK mill.)"], tt["Areal (m2)"])]
    tt["Brutto yield"] = [pct(l / p, 2) if pd.notna(l) and pd.notna(p) else "–" for l, p in zip(tt["Årlig leie (NOK mill.)"], tt["Pris (NOK mill.)"])]
    tab = pd.DataFrame({"Dato": tt["Dato"].astype(str).str[:7], "Eiendom": tt["Eiendom"].str.replace(r" \(bl\.a\..*\)", "", regex=True),
                        "Kjøper": tt["Kjøper"], "Pris (mill.)": [nr(v) if pd.notna(v) else "ikke oppgitt" for v in tt["Pris (NOK mill.)"]],
                        "m²": [nr(v) for v in tt["Areal (m2)"]], "kr/m²": tt["kr/m²"], "Brutto yield": tt["Brutto yield"]})
    r.table(tab, caption="Tabell 1. Sammenlignbare transaksjoner i Oslo-regionen 2024–2026. Pris per m² og brutto yield (leie / pris) er egne "
            "beregninger. Ingen kilde oppgir netto startyield for handlene.", index=False,
            col_widths=cmw([1.5, 5.6, 2.8, 1.9, 1.5, 1.4, 1.6]), font=7.2)
    r.image(FIG / "fig_transaksjoner.png", 15.0, "Figur 2. Budet ligger innenfor spennet i de største porteføljehandlene.")

    r.h1("3. Kontantstrøm og avkastning")
    r.p(f"Leien reguleres årlig med KPI for året før: {pct(M['kpi_2026'])} for 2026, {pct(M['kpi_2027'])} for 2027, {pct(M['kpi_2028'])} for 2028 og "
        f"{pct(M['kpi_2029'])} for 2029 (Norges Bank, PPR 3/2026), deretter {pct(M['kpi_lang'], 0)}. Eierkostnadene er satt til "
        f"{pct(A['eierkost'], 0)} av leien (Skatteetatens sjablong). Etter utløp står bygget tomt i {A['ledighet_mnd']} måneder. Så leies det ut "
        f"til markedsleie ({nr(A['markedsleie'])} kr/m² i 2026-kroner, KPI-justert), med en utleiekostnad på {pct(A['utleiekost'], 0)} av "
        f"første års leie. Bygget selges ved utgangen av 2036 på 2037-NOI til {pct(A['exit_yield'])}. Transaksjonskostnadene er "
        f"{pct(A['kjopskost'], 0)} ved kjøp og ved salg.")
    r.image(FIG / "fig_kontantstrom.png", 15.5, "Figur 3. NOI faller rundt utløpet og løftes så til markedsnivå.")
    kt = pd.DataFrame({"Nøkkeltall": ["Kjøpesum (bud)", "Kjøpesum per m²", "Netto / brutto startyield", "Salgsverdi 2036 (netto)",
                                      "IRR ufinansiert / multippel", f"IRR egenkapital ({pct(A['ltv'], 0)} LTV, {pct(A['rente'])} rente)",
                                      "Rentedekning år 1", "Maks pris ved 7,5 % krav (basis / 1 400 kr/m²)"],
                       "Verdi": [f"NOK {nr(X['pris'])} mill.", f"{nr(R['pris_m2'])} kr", f"{pct(R['netto_startyield'], 2)} / {pct(cf.iloc[0]['Brutto leie'] / X['pris'], 2)}",
                                 f"NOK {nr(R['exit'])} mill. ({nr(R['exit'] * 1e6 / M['areal'])} kr/m²)", f"{pct(R['irr'])} / {R['multippel']:.2f}x".replace(".", ","),
                                 f"{pct(R['irr_belant'])} / {R['multippel_belant']:.2f}x".replace(".", ","), f"{R['rentedekning_ar1']:.2f}x".replace(".", ","),
                                 f"NOK {nr(X['maks_bud'])} / {nr(Mo.resultat(None, markedsleie=M['markedsleie_langhus_lav'])['maks_bud'])} mill."]})
    r.table(kt, caption="Tabell 2. Avkastning ved budet, basis.", index=False, col_widths=cmw([8.5, 7.0]), font=8)
    r.p(f"Avkastningskravet på {pct(A['krav'])} er begrunnet på to måter, som gir omtrent samme svar. Den ene er prime yield "
        f"({pct(M['prime_yield_dnb'], 1)}) pluss inflasjonsmålet (2 %). Den andre er 10-årig statsrente ({pct(M['statsobligasjon_10y'], 2)}) pluss "
        f"3 prosentpoeng risikopremie. Rentedekningen på {R['rentedekning_ar1']:.2f}x".replace(".", ",") +
        f" i år 1 er lav. Belåningen gir dermed lite ekstra avkastning før leien er hevet, og bør holdes moderat.")

    r.h1("4. Sensitivitet: leienivå og exit-yield")
    r.image(FIG / "fig_sensitivitet.png", 14.0, "Figur 4. IRR ved budet for markedsleie ved reutleie × exit-yield.")
    st = pd.DataFrame({"Scenario": sc.index, "IRR ufinansiert": [pct(v) for v in sc["IRR"]], "IRR belånt": [pct(v) for v in sc["IRR belånt"]],
                       "Maks pris ved krav (mill.)": [nr(v) for v in sc["Maks bud"]]})
    r.table(st, caption=f"Tabell 3. Scenarier ved kjøpesum NOK {nr(X['pris'])} mill. «Dagens leie» er {nr(X['leie26_m2'])} kr/m² i 2026-kroner.",
            index=False, col_widths=cmw([7.5, 2.6, 2.4, 3.4]), font=8)
    g = X["grid"]
    r.p(f"Ved budet tåler caset nedre markedsleie ({nr(M['markedsleie_langhus_lav'])} kr/m²) og en exit-yield på 6,0 % og gir likevel "
        f"{pct(g.loc[1400, 0.06])}, nær kravet. Det som bryter caset, er en fornyelse uten leieøkning. Den er lite sannsynlig når markedet "
        f"ligger {(M['markedsleie_langhus_lav'] / X['leie26_m2'] - 1) * 100:.0f}–{pct(M['markedsleie_langhus_hoy'] / X['leie26_m2'] - 1, 0)} over dagens nivå, men NLP har sterk forhandlingsposisjon: de har drevet anlegget i 20 år og kan true med å flytte.")

    r.h1("5. Motpartsrisiko: Norsk Lastbærer Pool AS")
    nt = NT.T.astype(object)
    fmtd = {"Driftsinntekter (mill.)": lambda v: nr(v, 1), "Likviditetsgrad 1": lambda v: nr(v, 2),
            "Rentedekning": lambda v: f"{nr(v, 1)}x", "Leiedekning": lambda v: f"{nr(v, 1)}x", "Kontanter / årlig leie": lambda v: f"{nr(v, 1)}x"}
    for k in nt.index:
        nt.loc[k] = [("–" if pd.isna(v) else fmtd.get(k, pct)(v)) for v in nt.loc[k]]
    nt.columns = [str(c) for c in nt.columns]
    r.table(nt, caption="Tabell 4. NLPs nøkkeltall (Regnskapsregisteret; revidert av Deloitte). Leie = driftsinntektene til Fugleåsen 7 AS. "
            "Leiedekning = (driftsresultat + leie) / leie.", col_widths=cmw([6.0, 2.6, 2.6, 2.6]), font=8)
    r.bullets([
        "<b>Virksomhet:</b> NLP driver pool- og retursystemet for gjenbrukbare lastbærere i norsk dagligvare, med 42 ansatte. Selskapet eies "
        "50/50 av bransjeorganisasjonene DLF og DMF ifølge NLPs nettside (sitert i søk, siden kunne ikke åpnes herfra). Eierne er altså "
        "bransjen selv, og omsetningen følger volumene i dagligvarehandelen, som er stabile.",
        f"<b>Styrke:</b> omsetningen har vokst {pct(NT['Omsetningsvekst'].min(), 1)}–{pct(NT['Omsetningsvekst'].max(), 1)} i året, og driften går med overskudd hvert år. Egenkapitalandelen er {pct(NT.loc[2025, 'Egenkapitalandel'], 0)}, "
        f"og driftsresultatet før leie dekker leien {nr(NT.loc[2025, 'Leiedekning'], 1)} ganger. Kontantene alene tilsvarer "
        f"{nr(NT.loc[2025, 'Kontanter / årlig leie'], 1)} års leie.",
        f"<b>Svakhet:</b> marginen er tynn og fallende ({pct(NT.loc[2023, 'Driftsmargin'])} til {pct(NT.loc[2025, 'Driftsmargin'])}). Gjelden har økt, "
        f"og rentedekningen er falt fra {nr(NT.loc[2023, 'Rentedekning'], 1)}x til {nr(NT.loc[2025, 'Rentedekning'], 1)}x. Det skyldes trolig "
        "investeringer i lastbærere: anleggsmidlene har økt fra 213 til 330 mill. kr. Vi har ikke funnet noen offentlig kredittrating.",
        "<b>Vurdering:</b> lav risiko for mislighold i resten av leietiden. Risikoen sitter i fornyelsen i 2033, ikke i betalingsevnen. "
        "Før bud bør vi få leiekontrakten og bekrefte utløp, opsjoner, indeksering og eventuell morselskaps- eller bankgaranti.",
    ])

    r.h1("6. Risiko og begrensninger")
    r.bullets([
        "<b>Leien</b> er utledet av eierselskapets driftsinntekter, ikke av leiekontrakten. Inntektene kan inneholde annet, for eksempel strøm fra "
        "solcelleanlegget på 187 kWp eller viderefakturerte kostnader. Veksten i 2024 (7,6 %) var høyere enn KPI.",
        "<b>Utløpet</b> (30.9.2033) bygger på en avisartikkel fra 2012 om 20 års leietid og driftsstart i oktober 2013.",
        "<b>Eierkostnadene</b> (10 %) er en sjablong. Eierselskapets driftskostnader var 28 % av inntektene inklusive avskrivninger, men "
        "Regnskapsregisteret skiller ikke ut avskrivningene.",
        "<b>Markedsleie, exit-yield og avkastningskrav</b> er markedsanslag. Ingen offentlig kilde oppgir netto startyield for sammenlignbare "
        "handler eller en yield for sekundær logistikk.",
        "<b>Ikke modellert:</b> skatt og latent skatt i selskapet, lånekostnader og vedlikeholdsinvesteringer utover eierkostnadene.",
    ])
    r.p("<b>Kilder.</b> Regnskapsregisteret og Enhetsregisteret (Brønnøysundregistrene): Norsk Lastbærer Pool AS og Fugleåsen 7 AS. "
        "PEF kvartalsrapport Q3 2026 og bærekraftsrapport 2025 (paretoai.no). tungt.no / Logistikk & Ledelse 1.3.2012. Akershus Eiendom, "
        "Halvårsrapport høst 2026. DNB Næringsmegling, Sektoroppdatering lager og logistikk 21.9.2026. Catella Logistics Map Q2 2026. "
        "Newsec Property Outlook høst 2026. Norges Bank, Pengepolitisk rapport 3/2026 og rentestatistikk. Finanstilsynet, Finansielt "
        "utsyn juni 2026. Skatteetaten. MT Logistikk 22.12.2025. Konkurransetilsynet (sak 2025-0715). KLP/NTB og Colliers 15.6.2026. "
        "Wästbygg 16.4.2024. Logistikk Inside 10.6.2024. DNB Næringsmegling og Estate Nyheter om handler uten oppgitt pris.")
    print("sider:", r.build())
