"""Lager investorrapporten (PDF) for kvartalet som er valgt i model/kvartalsrapport_mal.xlsx (Input!B2).

Arbeidsboken regnes om i LibreOffice, nøkkeltallene leses fra arket «Nøkkeltall», og de viktigste kontrolleres mot en
uavhengig beregning i Python før rapporten skrives.

    python src/lag_rapport.py            # → report/investorrapport_<kvartal>.pdf
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT.parent)]
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
from openpyxl import load_workbook

from common.plotting import PALETTE, setup, source
from common.report import Report

plt = setup()
FIG = ROOT / "report" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
MAL = ROOT / "model" / "kvartalsrapport_mal.xlsx"
cmw = lambda ws: [w * 28.35 for w in ws]
pct = lambda x, d=1: f"{x * 100:.{d}f} %".replace(".", ",")
mill = lambda x: f"{x:,.0f}".replace(",", " ")
nr = lambda x, d=2: f"{x:.{d}f}".replace(".", ",")


def recalc(path):
    out = Path(tempfile.mkdtemp())
    subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx", "--outdir", str(out), str(path)],
                   check=True, capture_output=True, timeout=300)
    return load_workbook(out / path.name, data_only=True)


def table(ws, header_row=1):
    rows = [r for r in ws.iter_rows(min_row=header_row, values_only=True)]
    df = pd.DataFrame(rows[1:], columns=rows[0])
    return df.dropna(how="all")


wb = recalc(MAL)
N = {r[0]: r[1] for r in wb["Nøkkeltall"].iter_rows(min_row=2, values_only=True) if r[0]}
Q = N["Kvartal"]
I = wb["Input"]
qcols = [c.value for c in I[4][2:] if c.value]
INP = {r[0]: dict(zip(qcols, r[2:2 + len(qcols)])) for r in I.iter_rows(min_row=5, values_only=True) if r[0]}
E = table(wb["Eiendommer"])
U = table(wb["Utløpsprofil"])
H = table(wb["Historikk"], 3)
H = H[H["Avkastning"].notna()]
K = table(wb["Kontroller"], 3)
CF = table(wb["Kontantstrømmer"], 3)

# --- Uavhengig kontroll av nøkkeltallene i Python ------------------------------------------------------------------------
upto = H.iloc[:int(N["Løpenummer i Historikk"])]
chk = {"TVPI (utbetalt + VEK) / innkalt": (N["Akkumulerte utbetalinger (NOK mill.)"] + N["Verdijustert egenkapital, VEK (NOK mill.)"]) / N["Innkalt kapital (NOK mill.)"],
       "Aggregert siden oppstart (kjedet)": float(np.prod(1 + upto["Avkastning"].astype(float)) - 1),
       "Siste 12 måneder (fire kvartaler kjedet)": float(np.prod(1 + upto["Avkastning"].astype(float).tail(4)) - 1),
       "Økonomisk utleiegrad (1 − ledighet)": 1 - N["Økonomisk ledighet"]}
t = (pd.to_datetime(CF["Dato"]) - pd.to_datetime(CF["Dato"]).min()).dt.days / 365.0
amt = CF["Beløp"].astype(float).values
lo, hi = -0.9, 1.0
for _ in range(200):
    mid = (lo + hi) / 2
    lo, hi = (mid, hi) if (amt / (1 + mid) ** t.values).sum() > 0 else (lo, mid)
chk["IRR for perioden i Kontantstrømmer (XIRR)"] = (lo + hi) / 2
for k, v in chk.items():
    assert abs(N[k] - v) < 5e-4, (k, N[k], v)
print("Excel og Python stemmer for", len(chk), "nøkkeltall")

# --- Figurer -------------------------------------------------------------------------------------------------------------
yr = H.groupby("År").apply(lambda g: float(np.prod(1 + g["Avkastning"].astype(float)) - 1), include_groups=False)
pay = H.groupby("År")["Utbetaling i % av innbetalt kapital"].sum()
fig, ax = plt.subplots(figsize=(9, 3.6))
x = np.arange(len(yr))
ax.bar(x - 0.2, yr.values * 100, 0.4, color=PALETTE[0], label="Totalavkastning (kjedet)")
ax.bar(x + 0.2, pay.reindex(yr.index).values * 100, 0.4, color=PALETTE[1], label="Utbetaling i % av innbetalt kapital")
ax.axhline(0, color="black", lw=0.7)
ax.set_xticks(x, [str(y) if y != yr.index[-1] else f"{y}\n(hittil)" for y in yr.index], fontsize=7.5)
ax.set_ylabel("%"); ax.legend(fontsize=8); ax.set_title("Årlig avkastning og utbetaling siden oppstart")
source(ax, "Kilde: PEF kvartalsrapport Q3 2026 (s. 6); egne beregninger.")
fig.savefig(FIG / "fig_avkastning.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 3.2))
ax.bar(U["År"].astype(int).astype(str), U["Andel av leieinntekter"].astype(float) * 100, color=PALETTE[0])
for i, v in enumerate(U["Andel av leieinntekter"].astype(float)):
    ax.text(i, v * 100 + 0.4, f"{v * 100:.1f}".replace(".", ","), ha="center", fontsize=7)
ax.set_ylabel("% av leieinntekter"); ax.set_title(f"Utløpsprofil på leiekontraktene, {Q}")
source(ax, f"Kilde: PEF kvartalsrapport {Q} (s. 8).")
fig.savefig(FIG / "fig_utlop.png"); plt.close(fig)

EO = E[E["Leietaker"] != "Ledig areal"]
kom = E.groupby("Kommune")["Areal (kvm)"].sum().sort_values()
fig, axs = plt.subplots(1, 2, figsize=(10, 3.6))
axs[0].barh(kom.index, kom.values / 1000, color=PALETTE[0]); axs[0].set_xlabel("1 000 kvm"); axs[0].set_title("Areal per kommune", fontsize=10)
qs = [q for q in qcols if INP["Brutto eiendomsverdi"].get(q)]
axs[1].plot(qs, [INP["Brutto eiendomsverdi"][q] for q in qs], marker="o", color=PALETTE[0], label="Brutto eiendomsverdi")
axs[1].plot(qs, [INP["VEK"][q] for q in qs], marker="s", color=PALETTE[1], label="VEK")
axs[1].plot(qs, [INP["Innkalt kapital"][q] for q in qs], marker="^", color=PALETTE[2], label="Innkalt kapital")
axs[1].set_ylabel("NOK mill."); axs[1].legend(fontsize=7.5); axs[1].set_title("Verdier per kvartal", fontsize=10)
axs[1].yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", " ")))
source(axs[0], f"Kilde: PEF kvartalsrapporter 2026; eiendomsliste {Q}.")
fig.tight_layout(); fig.savefig(FIG / "fig_portefolje.png"); plt.close(fig)

# --- Rapport -------------------------------------------------------------------------------------------------------------
r = Report(ROOT / "report" / f"investorrapport_{Q.replace(' ', '_')}.pdf", f"Investorrapport {Q}: Pareto Eiendomsfellesskap IS/AS",
           "Egen versjon av kvartalsrapporten, laget fra malen model/kvartalsrapport_mal.xlsx · tall i NOK mill. der ikke annet er angitt")
r.h1("Sammendrag")
r.abstract(
    f"Fondet eier {N['Antall bygg']:.0f} logistikkbygg på til sammen {mill(N['Areal (kvm)'])} kvm, med {N['Antall leietakere']:.0f} leietakere. "
    f"Brutto eiendomsverdi er NOK {mill(N['Brutto eiendomsverdi (NOK mill.)'])} mill., og brutto annualiserte leieinntekter er "
    f"NOK {mill(N['Brutto annualiserte leieinntekter (NOK mill.)'])} mill. Den økonomiske utleiegraden er {pct(N['Økonomisk utleiegrad (1 − ledighet)'])}, "
    f"og vektet gjenværende leietid er {nr(N['Vektet gjenværende leietid (år)'], 1)} år. Avkastningen i kvartalet var {pct(N['Kvartalets avkastning'])}, "
    f"{pct(N['Siste 12 måneder (fire kvartaler kjedet)'])} de siste tolv månedene (kjedet) og {pct(N['IRR siden oppstart, rapportert av forvalter'])} "
    f"per år siden 2009 (IRR, rapportert). Investorene har fått utbetalt {pct(N['Utbetalt i % av innkalt kapital'])} av innkalt kapital "
    f"(DPI {nr(N['DPI (utbetalt / innkalt)'])}x). Samlet verdi per innkalt krone er {nr(N['TVPI (utbetalt + VEK) / innkalt'])}x (TVPI).")
kt = pd.DataFrame([
    ("Brutto eiendomsverdi", f"NOK {mill(N['Brutto eiendomsverdi (NOK mill.)'])} mill."),
    ("Verdi per kvm", f"NOK {mill(N['Eiendomsverdi per kvm (NOK)'])}"),
    ("Brutto annualiserte leieinntekter", f"NOK {mill(N['Brutto annualiserte leieinntekter (NOK mill.)'])} mill. (leie per kvm NOK {mill(N['Leie per kvm (NOK)'])})"),
    ("Økonomisk utleiegrad / ledighet", f"{pct(N['Økonomisk utleiegrad (1 − ledighet)'])} / {pct(N['Økonomisk ledighet'])}"),
    ("Vektet gjenværende leietid", f"{nr(N['Vektet gjenværende leietid (år)'], 1)} år"),
    ("Netto yield / justert for ledighet", f"{pct(N['Netto yield (eiendomsnivå)'])} / {pct(N['Netto yield justert for ledighet'])}"),
    ("Kvartalets avkastning", pct(N["Kvartalets avkastning"])),
    ("Hittil i år / siste 12 mnd (kjedet)", f"{pct(N['Hittil i år (kjedet)'])} / {pct(N['Siste 12 måneder (fire kvartaler kjedet)'])}"),
    ("IRR siden oppstart (rapportert) / kjedet annualisert", f"{pct(N['IRR siden oppstart, rapportert av forvalter'])} / {pct(N['Annualisert siden oppstart (kjedet)'])}"),
    ("Direkteavkastning: utbetaling siste fire kvartaler", f"{pct(N['Utbetaling siste fire kvartaler (% av innbetalt kapital)'])} av innbetalt kapital"),
    ("DPI / RVPI / TVPI", f"{nr(N['DPI (utbetalt / innkalt)'])}x / {nr(N['RVPI (VEK / innkalt)'])}x / {nr(N['TVPI (utbetalt + VEK) / innkalt'])}x"),
], columns=["Nøkkeltall", Q])
r.table(kt, caption="Tabell 1. Nøkkeltall. Alle tall er hentet fra arket «Nøkkeltall» i malen.", index=False, col_widths=cmw([7.5, 8.5]), font=8.5)

r.h1("1. Porteføljestatus")
r.p(f"Porteføljen består av lager- og terminalbygg, hovedsakelig i Oslo-området. Det største bygget er {EO.iloc[0]['Eiendom']} "
    f"({mill(EO.iloc[0]['Areal (kvm)'])} kvm). Ledig areal i eiendomslisten er {mill(E.loc[E['Leietaker'] == 'Ledig areal', 'Areal (kvm)'].sum())} kvm "
    f"på Snipetjernveien 4. Der gikk leietakeren Merkur Grafisk konkurs sommeren 2026, og leiegarantien som er stilt dekker leien "
    f"inntil videre. Den arealmessige utleiegraden er {pct(N['Arealmessig utleiegrad (eiendomslisten)'])}.")
r.image(FIG / "fig_portefolje.png", 16.0, "Figur 1. Areal per kommune og utvikling i verdier gjennom 2026.")
et = E.copy()
et["Areal (kvm)"] = et["Areal (kvm)"].map(mill)
r.table(et[["Eiendom", "Kommune", "Segment", "Leietaker", "Areal (kvm)"]],
        caption=f"Tabell 2. Eiendomsportefølje {Q} (kvartalsrapporten s. 9–10).", index=False,
        col_widths=cmw([3.4, 2.4, 2.8, 6.2, 1.8]), font=6.8)

r.h1("2. Leieinntekter og utleiegrad")
prev_rent = INP["Brutto annualiserte leieinntekter"]
r.p(f"Brutto annualiserte leieinntekter er NOK {mill(N['Brutto annualiserte leieinntekter (NOK mill.)'])} mill., "
    f"{'uendret' if not N['Endring fra forrige kvartal (NOK mill.)'] else 'en endring på NOK ' + mill(N['Endring fra forrige kvartal (NOK mill.)']) + ' mill.'} "
    f"fra forrige kvartal. Leieinntektene har økt fra NOK {mill(prev_rent[qcols[0]])} mill. i {qcols[0]}, hovedsakelig fordi fire bygg kom til "
    f"i 2. kvartal. {pct(N['Andel KPI-regulert'], 0)} av leieinntektene KPI-reguleres årlig. Kontraktene som går ut innen "
    f"2028 utgjør {pct(float(U.loc[U['År'].astype(int) <= 2028, 'Andel av leieinntekter'].sum()))} av leieinntektene, og det største "
    f"utløpsåret er {int(U.loc[U['Andel av leieinntekter'].astype(float).idxmax(), 'År'])}.")
r.image(FIG / "fig_utlop.png", 15.5, "Figur 2. Andel av leieinntektene som går ut hvert år.")

r.h1("3. Avkastning")
r.image(FIG / "fig_avkastning.png", 15.5, "Figur 3. Årlig totalavkastning og utbetaling, 2010 – 2026 hittil.")
r.bullets([
    f"<b>Direkteavkastning:</b> fondet har utbetalt {pct(N['Utbetaling siste fire kvartaler (% av innbetalt kapital)'])} av innbetalt kapital de siste "
    f"fire kvartalene, og {pct(N['Annualisert utbytte (4 × kvartalets) i % av VEK'])} av VEK på årsbasis. På eiendomsnivå er netto yield "
    f"{pct(N['Netto yield (eiendomsnivå)'])}, og {pct(N['Netto yield justert for ledighet'])} når ledig areal regnes som utleid til markedsleie.",
    f"<b>IRR:</b> forvalter oppgir {pct(N['IRR siden oppstart, rapportert av forvalter'])} per år siden 2009. Kvartalstallene kjedet og "
    f"annualisert gir {pct(N['Annualisert siden oppstart (kjedet)'], 2)}. For perioden 31.03–30.09.2026 gir de daterte kontantstrømmene "
    f"(VEK, innkallinger og utbytte) en IRR på {pct(N['IRR for perioden i Kontantstrømmer (XIRR)'], 2)} per år, som tilsvarer "
    f"{pct(N['Samme, omregnet til perioden'], 2)} for halvåret. Q2 og Q3 kjedet gir {pct(float(np.prod(1 + upto['Avkastning'].astype(float).tail(2)) - 1))}.",
    f"<b>Multipler:</b> DPI {nr(N['DPI (utbetalt / innkalt)'])}x, RVPI {nr(N['RVPI (VEK / innkalt)'])}x og TVPI {nr(N['TVPI (utbetalt + VEK) / innkalt'])}x. "
    f"Om lag to tredeler av utbyttet reinvesteres i fondet (68 % i Q3), så det meste av verdien ligger fortsatt i VEK.",
])

r.h1("4. Kontroller")
kc = K.copy()
fmt = lambda v: "" if v is None or v == "" else (nr(v, 4) if isinstance(v, float) and abs(v) < 5 else mill(v) if isinstance(v, (int, float)) else str(v))
for c in ["Beregnet", "Rapportert", "Avvik", "Toleranse"]:
    kc[c] = kc[c].map(fmt)
r.table(kc, caption="Tabell 3. Avstemming i malen (arket «Kontroller»). Andeler er vist som desimaltall.", index=False,
        col_widths=cmw([8.2, 2.0, 2.0, 2.0, 1.8]), font=7.2)
r.p("Merknader til kontrollene:")
r.bullets([
    "Kjedede kvartalstall gir 255,9 % mot rapportert 255,2 %. Avviket skyldes at kvartalstallene er avrundet til én desimal.",
    "Eiendomslisten summerer til 480 824 kvm mot oppgitt 480 823 kvm.",
    "VEK-broen for Q2 gir 1,44 % mot rapportert 1,6 %. Rapporten oppgir ikke datoen for innkallingen av ny kapital. Malen antar "
    "26. juni, da kapitalinnhentingen ble avsluttet. Emisjonskostnader periodiseres i VEK. Begge deler påvirker IRR for kvartalet.",
    "Utbetalingstabellen i Q3-rapporten viser 1,5 % for Q2 2026, mens Q2-rapporten oppga 1,4 %.",
])
r.h1("Definisjoner og kilder")
r.p("<b>Økonomisk utleiegrad</b> = 1 − økonomisk ledighet. <b>Direkteavkastning</b> = utbetalinger i % av innbetalt kapital, og netto "
    "yield på eiendomsnivå. <b>DPI</b> = akkumulerte utbetalinger / innkalt kapital. <b>RVPI</b> = VEK / innkalt kapital. <b>TVPI</b> = DPI + RVPI. "
    "<b>IRR</b> = XIRR på daterte kontantstrømmer med VEK ved start og slutt. <b>Kjedet avkastning</b> = produktet av (1 + kvartalsavkastning). "
    "Kilder: Pareto Eiendomsfellesskap IS/AS, kvartalsrapporter Q1, Q2 og Q3 2026 (paretoai.no/reports). Dette er en egen "
    "fremstilling og ikke et dokument fra Pareto Alternative Investments.")
print("sider:", r.build())
