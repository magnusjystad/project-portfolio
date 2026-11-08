// Bygger PowerPoint-versjonen av investeringsmemoet for Fugleåsen 7 med pptxgenjs.
// Kalles fra src/lag_pptx.py:  node src/lag_pptx.js <data.json> <ut.pptx>
const fs = require("fs");
const pptxgen = require("pptxgenjs");

const [, , dataFil, utFil] = process.argv;
const d = JSON.parse(fs.readFileSync(dataFil, "utf8"));

// Farger: mørk skifer, teal og rav (logistikk, betong og varsellys)
const DARK = "1F3A3D", TEAL = "3E7C7B", AMBER = "D9822B", LIGHT = "EEF2F1", TEXT = "1E2B2C", MUTED = "5B6B6B", WHITE = "FFFFFF";
const HFONT = "Cambria", BFONT = "Calibri";

const nb = (x, dec = 0) => {
  const s = Math.abs(x).toFixed(dec).split(".");
  s[0] = s[0].replace(/\B(?=(\d{3})+(?!\d))/g, "\u00A0");
  return (x < 0 ? "−" : "") + s.join(",");
};
const pc = (x, dec = 1) => nb(x * 100, dec) + "\u00A0%"; // hardt mellomrom: tall og enhet brytes ikke
const spenn = (a, b) => (Math.round(a * 100) === Math.round(b * 100) ? `om lag ${pc(a, 0)}` : `${nb(a * 100, 0)}–${pc(b, 0)}`);

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13,33 × 7,5 tommer
pres.author = "Investment Research Portfolio";
pres.title = "Fugleåsen 7: investeringscase";
pres.theme = { headFontFace: HFONT, bodyFontFace: BFONT };

pres.defineSlideMaster({
  title: "MORK",
  background: { color: DARK },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 2.2, w: 11.9, h: 1.3, fontFace: HFONT, fontSize: 42, bold: true, color: WHITE, align: "left", valign: "bottom", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.7, y: 3.65, w: 11.9, h: 1.4, fontFace: BFONT, fontSize: 20, color: "CFE0DD", valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "INNHOLD",
  background: { color: WHITE },
  margin: [0.5, 0.6, 0.6, 0.6],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.3, w: 12.1, h: 0.9, fontFace: HFONT, fontSize: 30, bold: true, color: DARK, align: "left", valign: "middle", margin: 0 }, text: "" } },
    { text: { text: "Fugleåsen 7, Langhus · investeringscase · oktober 2026", options: { x: 0.6, y: 7.0, w: 8, h: 0.3, fontFace: BFONT, fontSize: 10, color: MUTED, margin: 0 } } },
  ],
  slideNumber: { x: 12.3, y: 7.0, w: 0.4, h: 0.3, fontFace: BFONT, fontSize: 10, color: MUTED, align: "right" },
});

const kilde = (s, txt) => s.addText(txt, { x: 0.6, y: 6.6, w: 12.1, h: 0.3, fontSize: 10, color: MUTED, italic: true, margin: 0, isTextBox: true });

function statKort(s, x, y, w, h, tall, tekst, farge = DARK) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: LIGHT }, line: { color: LIGHT }, rectRadius: 0.08 });
  s.addText(tall, { x: x + 0.2, y: y + 0.15, w: w - 0.4, h: h * 0.55, fontFace: HFONT, fontSize: 34, bold: true, color: farge, valign: "bottom", margin: 0, isTextBox: true });
  s.addText(tekst, { x: x + 0.2, y: y + 0.18 + h * 0.55, w: w - 0.4, h: h * 0.4 - 0.2, fontSize: 13, color: MUTED, valign: "top", margin: 0, isTextBox: true });
}

function punktKort(s, x, y, w, h, overskrift, tekst, farge = TEAL) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: LIGHT }, line: { color: LIGHT }, rectRadius: 0.08 });
  s.addShape(pres.shapes.OVAL, { x: x + 0.2, y: y + 0.22, w: 0.32, h: 0.32, fill: { color: farge }, line: { color: farge } });
  s.addText(overskrift, { x: x + 0.65, y: y + 0.15, w: w - 0.85, h: 0.45, fontSize: 16, bold: true, color: TEXT, valign: "middle", margin: 0, isTextBox: true });
  s.addText(tekst, { x: x + 0.2, y: y + 0.7, w: w - 0.4, h: h - 0.85, fontSize: 14, color: TEXT, valign: "top", margin: 0, isTextBox: true });
}

const akse = { catAxisLabelColor: MUTED, valAxisLabelColor: MUTED, catAxisLabelFontFace: BFONT, valAxisLabelFontFace: BFONT,
  catAxisLabelFontSize: 12, valAxisLabelFontSize: 11, valGridLine: { color: "D9DFDE", size: 0.5 }, catGridLine: { style: "none" },
  dataLabelFontFace: BFONT, dataLabelFontSize: 11, dataLabelColor: TEXT, titleFontFace: BFONT, titleColor: TEXT, titleFontSize: 14,
  legendFontFace: BFONT, legendFontSize: 12 };

// 1 Tittel
pres.addSection({ title: "Anbefaling" });
let s = pres.addSlide({ masterName: "MORK", sectionTitle: "Anbefaling" });
s.addText("Fugleåsen 7, Langhus", { placeholder: "title" });
s.addText(`Investeringscase: ${nb(d.areal)} m² lager og logistikk, utleid til Norsk Lastbærer Pool AS\nOktober 2026`, { placeholder: "body" });

// 2 Anbefaling
s = pres.addSlide({ masterName: "INNHOLD", sectionTitle: "Anbefaling" });
s.addText(`Vi anbefaler å by NOK ${nb(d.pris)} mill.`, { placeholder: "title" });
const kort = [[`${nb(d.pris)} mill.`, `Bud (${nb(d.pris_m2)} kr/m²)`, AMBER], [pc(d.irr), "IRR ufinansiert, 10 år (krav 7,5 %)", DARK],
  [pc(d.irr_bel), `IRR egenkapital, ${pc(d.A.ltv, 0)} belåning`, DARK], [pc(d.startyield, 2), "Netto startyield", DARK]];
kort.forEach((k, i) => statKort(s, 0.6 + i * 3.1, 1.45, 2.85, 1.9, k[0], k[1], k[2]));
const punkter = [
  ["Lav leie gir oppside", `NLP betaler ${nb(d.leie26_m2)} kr/m². Markedsleien på Langhus er ${nb(d.M.markedsleie_langhus_lav)}–${nb(d.M.markedsleie_langhus_hoy)} kr/m². Kontrakten utløper trolig 30.9.2033.`],
  ["Vi byr forsiktig", `Maks pris i basis er NOK ${nb(d.maks_bud)} mill. Vi byr ut fra nedre markedsleie og betaler ikke fullt for reutleiegevinsten (${pc(d.rev_andel, 0)} av verdien).`],
  ["Risikoen er fornyelsen", `Fornyer NLP til dagens leie, faller IRR til ${pc(d.scen[2].irr)}. Betalingsevnen er god: egenkapitalandel ${pc(d.nlp["2025"].ek, 0)}.`],
];
punkter.forEach((p, i) => punktKort(s, 0.6 + i * 4.1, 3.7, 3.85, 2.4, p[0], p[1], i === 2 ? AMBER : TEAL));

// 3 Eiendommen og leien
pres.addSection({ title: "Eiendom og marked" });
s = pres.addSlide({ masterName: "INNHOLD", sectionTitle: "Eiendom og marked" });
s.addText("NLP betaler under markedsleien på Langhus", { placeholder: "title" });
const fakta = [
  ["Bygget", "Driftsstasjon og mellomlager, ferdig oktober 2013. Energimerke A (lager) og B (kontor)."],
  ["Eier i dag", "PEF gjennom Fugleåsen 7 AS. Utgjorde 4 % av PEFs eiendeler i 2025."],
  ["Leieavtalen", "20 år med Bulk Eiendom fra 2013, så utløp rundt 30.9.2033. Opsjoner og indeksering er ikke offentlige."],
  ["Leien", `${nb(d.M.leie_2025, 2)} mill. kr i 2025 (eierselskapets inntekter), KPI-regulert til ${nb(d.leie26_m2)} kr/m² i 2026.`],
];
fakta.forEach((f, i) => {
  s.addText([{ text: f[0], options: { bold: true, color: DARK, breakLine: true } }, { text: f[1], options: { color: TEXT } }],
    { x: 0.6, y: 1.45 + i * 1.25, w: 5.6, h: 1.15, fontSize: 14, valign: "top", margin: 0, isTextBox: true });
});
s.addChart(pres.charts.BAR, [{ name: "kr/m²", labels: ["Fugleåsen 7 (2026)", "PEF snitt", "Langhus lav", "Langhus høy", "Oslo prime"],
  values: [d.leie26_m2, d.M.pef_leie_snitt, d.M.markedsleie_langhus_lav, d.M.markedsleie_langhus_hoy, d.M.markedsleie_prime_oslo] }],
  { x: 6.6, y: 1.35, w: 6.1, h: 5.1, barDir: "col", chartColors: [AMBER, TEAL, TEAL, TEAL, TEAL], showValue: true, dataLabelPosition: "outEnd",
    dataLabelFormatCode: "# ##0", valAxisLabelFormatCode: "# ##0", showLegend: false, showTitle: true, title: "Leie, NOK per m² per år", ...akse });
kilde(s, "Kilder: tungt.no 1.3.2012; PEF Q3 2026 og bærekraftsrapport 2025; Regnskapsregisteret; Akershus Eiendom høst 2026.");

// 4 Marked og transaksjoner
s = pres.addSlide({ masterName: "INNHOLD", sectionTitle: "Eiendom og marked" });
s.addText("Budet ligger innenfor nylige handler per m²", { placeholder: "title" });
const hode = ["Handel", "År", "Kjøper", "Pris (mill.)", "m²", "kr/m²", "Brutto yield"].map((t) => ({ text: t, options: { bold: true, color: WHITE, fill: { color: DARK } } }));
const rader = d.comps.map((c) => [c.navn, c.aar, c.kjoper, nb(c.pris), nb(c.areal), nb(c.kr_m2), c.yield ? pc(c.yield, 2) : "–"]);
rader.push([{ text: "Fugleåsen 7 ved budet", options: { bold: true } }, "2026", "–", nb(d.pris), nb(d.areal),
  { text: nb(d.pris_m2), options: { bold: true } }, pc(d.brutto_yield, 2)].map((v) => (typeof v === "string" ? { text: v, options: { bold: true, fill: { color: "FBE9D6" } } } : { ...v, options: { ...v.options, fill: { color: "FBE9D6" } } })));
s.addTable([hode, ...rader], { x: 0.6, y: 1.4, w: 12.1, colW: [4.0, 0.8, 2.2, 1.3, 1.2, 1.2, 1.4], fontSize: 13, fontFace: BFONT, color: TEXT,
  border: { type: "solid", pt: 0.5, color: "D9DFDE" }, valign: "middle", rowH: 0.45 });
[[pc(d.M.prime_yield_ae, 2), "Prime yield, Akershus Eiendom"], [pc(d.M.prime_yield_dnb, 2), "Prime yield, DNB Næringsmegling"],
  [pc(d.M.pef_netto_yield, 1), "PEF-porteføljen, netto yield (vår exit-yield)"]].forEach((k, i) => statKort(s, 0.6 + i * 4.1, 4.45, 3.85, 1.8, k[0], k[1], i === 2 ? AMBER : DARK));
kilde(s, "Kilder: MT Logistikk; KLP/NTB; Colliers; Wästbygg; Logistikk Inside; Akershus Eiendom; DNB Næringsmegling; PEF Q3 2026. Pris per m² og yield er egne beregninger.");

// 5 Kontantstrøm
pres.addSection({ title: "Avkastning" });
s = pres.addSlide({ masterName: "INNHOLD", sectionTitle: "Avkastning" });
s.addText("NOI faller rundt utløpet i 2033 og løftes så", { placeholder: "title" });
const aarTekst = d.aar.map(String);
s.addChart([
  { type: pres.charts.BAR, data: [{ name: "Netto driftsinntekt (NOI)", labels: aarTekst, values: d.noi }], options: { barDir: "col", chartColors: [TEAL] } },
  { type: pres.charts.LINE, data: [{ name: "NOI om NLP-leien fortsatte", labels: aarTekst, values: d.noi_kontrakt }], options: { chartColors: [AMBER], lineSize: 2, lineDash: "dash", lineDataSymbol: "none" } },
], { x: 0.6, y: 1.35, w: 7.7, h: 5.1, showLegend: true, legendPos: "b", showTitle: true, title: "NOK mill. per år, basis", valAxisLabelFormatCode: "0", ...akse });
const ks = [["Utløp og ledighet", `Kontrakten utløper 30.9.2033. Deretter er bygget ${d.A.ledighet_mnd} mnd tomt, og utleiekostnaden er ${pc(d.A.utleiekost, 0)} av første års leie.`],
  ["Ny leie", `${nb(d.A.markedsleie)} kr/m² i 2026-kroner, KPI-justert. Fra 2035 er NOI ${pc(d.noi[8] / d.noi_kontrakt[8] - 1, 0)} høyere enn med NLP-leien.`],
  ["Salg 2036", `På 2037-NOI til ${pc(d.A.exit_yield, 1)}: NOK ${nb(d.exit)} mill. etter kostnader.`]];
ks.forEach((k, i) => punktKort(s, 8.6, 1.35 + i * 1.75, 4.1, 1.62, k[0], k[1], i === 1 ? AMBER : TEAL));
kilde(s, "Leie: Regnskapsregisteret. KPI: Norges Bank PPR 3/2026, 2 % fra 2030. Eierkostnader 10 % (Skatteetatens sjablong).");

// 6 Nøkkeltall
s = pres.addSlide({ masterName: "INNHOLD", sectionTitle: "Avkastning" });
s.addText(`${pc(d.irr)} IRR ved budet, mot krav på ${pc(d.A.krav)}`, { placeholder: "title" });
const nk = [["Kjøpesum (bud)", `NOK ${nb(d.pris)} mill.`], ["Pris per m²", `${nb(d.pris_m2)} kr`], ["Netto / brutto startyield", `${pc(d.startyield, 2)} / ${pc(d.brutto_yield, 2)}`],
  ["IRR / multippel, ufinansiert", `${pc(d.irr)} / ${nb(d.mult, 2)}x`], [`IRR / multippel, egenkapital (${pc(d.A.ltv, 0)} LTV, ${pc(d.A.rente)})`, `${pc(d.irr_bel)} / ${nb(d.mult_bel, 2)}x`],
  ["Rentedekning år 1", `${nb(d.icr, 2)}x`], ["Maks pris ved krav: basis / 1 400 kr/m²", `NOK ${nb(d.maks_bud)} / ${nb(d.maks_lav)} mill.`]];
s.addTable(nk.map((r, i) => [{ text: r[0], options: { color: TEXT, fill: { color: i % 2 ? WHITE : LIGHT } } }, { text: r[1], options: { bold: true, color: DARK, align: "right", fill: { color: i % 2 ? WHITE : LIGHT } } }]),
  { x: 0.6, y: 1.45, w: 7.6, colW: [5.0, 2.6], fontSize: 15, fontFace: BFONT, rowH: 0.62, valign: "middle", border: { type: "none" } });
punktKort(s, 8.6, 1.45, 4.1, 2.35, "Avkastningskravet", "Prime yield 5,5 % pluss KPI-målet 2 %, eller 10-års stat 4,4 % pluss 3 prosentpoeng premie. Begge gir om lag 7,5 %.");
punktKort(s, 8.6, 4.05, 4.1, 2.35, "Moderat belåning", `Rentedekningen er bare ${nb(d.icr, 2)}x før leien heves. Med lånerente ${pc(d.A.rente)} gir belåning lite før 2035.`, AMBER);

// 7 Sensitivitet
s = pres.addSlide({ masterName: "INNHOLD", sectionTitle: "Avkastning" });
s.addText("Caset tåler nedre markedsleie, men ikke høy exit-yield samtidig", { placeholder: "title" });
const farge = (v) => { // rød (4 %) – gul (7,5 %) – grønn (11 %)
  const lerp = (a, b, t) => Math.round(a + (b - a) * Math.max(0, Math.min(1, t)));
  const [r1, g1, b1] = v < 0.075 ? [248, 105, 107] : [255, 235, 132];
  const [r2, g2, b2] = v < 0.075 ? [255, 235, 132] : [99, 190, 123];
  const t = v < 0.075 ? (v - 0.04) / 0.035 : (v - 0.075) / 0.035;
  return [lerp(r1, r2, t), lerp(g1, g2, t), lerp(b1, b2, t)].map((x) => x.toString(16).padStart(2, "0")).join("").toUpperCase();
};
const gh = [{ text: "kr/m² \\ exit-yield", options: { bold: true, color: WHITE, fill: { color: DARK } } },
  ...d.grid.yield.map((y) => ({ text: pc(y, 2), options: { bold: true, color: WHITE, fill: { color: DARK }, align: "center" } }))];
const gr = d.grid.leie.map((l, i) => [{ text: nb(l), options: { bold: true, fill: { color: LIGHT } } },
  ...d.grid.irr[i].map((v, j) => ({ text: pc(v), options: { align: "center", fill: { color: farge(v) },
    bold: l === d.A.markedsleie && Math.abs(d.grid.yield[j] - d.A.exit_yield) < 1e-9 } }))]);
s.addTable([gh, ...gr], { x: 0.6, y: 1.4, w: 8.4, colW: [1.75, ...d.grid.yield.map(() => 0.95)], fontSize: 13, fontFace: BFONT, color: TEXT,
  rowH: 0.56, valign: "middle", border: { type: "solid", pt: 0.75, color: WHITE } });
punktKort(s, 9.4, 1.4, 3.3, 2.35, "Slik leses den", `IRR ved kjøpesum NOK ${nb(d.pris)} mill. Rader: markedsleie ved reutleie i 2026-kroner. Kolonner: exit-yield. Fet = basis.`);
punktKort(s, 9.4, 4.0, 3.3, 2.35, "Terskel", `Ved 1 400 kr/m² og 6,0 % exit-yield er IRR ${pc(d.grid.irr[1][4])}, nær kravet på ${pc(d.A.krav)}.`, AMBER);
kilde(s, "Egen modell. Samme gitter ligger i Excel-modellen, arket Sensitivitet.");

// 8 Scenarier
s = pres.addSlide({ masterName: "INNHOLD", sectionTitle: "Avkastning" });
s.addText("Fornyelse til dagens leie er scenariet som bryter caset", { placeholder: "title" });
s.addChart(pres.charts.BAR, [{ name: "IRR ufinansiert", labels: d.scen.map((x) => x.navn), values: d.scen.map((x) => x.irr * 100) },
  { name: "IRR egenkapital", labels: d.scen.map((x) => x.navn), values: d.scen.map((x) => x.irr_bel * 100) }],
  { x: 0.6, y: 1.35, w: 8.2, h: 5.1, barDir: "col", barGrouping: "clustered", chartColors: [TEAL, AMBER], showValue: true, dataLabelPosition: "outEnd",
    dataLabelFormatCode: "0.0", valAxisLabelFormatCode: "0", showLegend: true, legendPos: "b", showTitle: true,
    title: `IRR i prosent ved kjøpesum NOK ${nb(d.pris)} mill.`, ...akse, catAxisLabelFontSize: 11 });
punktKort(s, 9.1, 1.35, 3.6, 2.45, "Mest sannsynlig", `Markedet ligger ${spenn(d.M.markedsleie_langhus_lav / d.leie26_m2 - 1, d.M.markedsleie_langhus_hoy / d.leie26_m2 - 1)} over dagens leie. Fornyer NLP til markedsleie uten ledighet, gir det ${pc(d.scen[1].irr)}.`);
punktKort(s, 9.1, 4.0, 3.6, 2.45, "Forhandlingsrisiko", `NLP har drevet anlegget i 20 år og kan true med å flytte. Fornyelse til dagens leie gir bare ${pc(d.scen[2].irr)}.`, AMBER);

// 9 Motpart
pres.addSection({ title: "Leietaker og neste steg" });
s = pres.addSlide({ masterName: "INNHOLD", sectionTitle: "Leietaker og neste steg" });
s.addText("NLP er en solid motpart med lav og stabil risiko", { placeholder: "title" });
const yr = Object.keys(d.nlp);
const nh = [{ text: "NOK mill. / nøkkeltall", options: { bold: true, color: WHITE, fill: { color: DARK } } }, ...yr.map((y) => ({ text: y, options: { bold: true, color: WHITE, fill: { color: DARK }, align: "right" } }))];
const linjer = [["Driftsinntekter", (v) => nb(v.oms, 1)], ["Driftsmargin", (v) => pc(v.margin)], ["Egenkapitalandel", (v) => pc(v.ek)],
  ["Rentedekning", (v) => nb(v.rd, 1) + "x"], ["Leie / driftsinntekter", (v) => pc(v.leie_andel)], ["Leiedekning", (v) => nb(v.leiedekning, 1) + "x"],
  ["Kontanter / årlig leie", (v) => nb(v.kontanter_leie, 1) + "x"]];
s.addTable([nh, ...linjer.map((l, i) => [{ text: l[0], options: { fill: { color: i % 2 ? WHITE : LIGHT } } },
  ...yr.map((y) => ({ text: l[1](d.nlp[y]), options: { align: "right", fill: { color: i % 2 ? WHITE : LIGHT } } }))])],
  { x: 0.6, y: 1.4, w: 6.6, colW: [3.0, 1.2, 1.2, 1.2], fontSize: 14, fontFace: BFONT, color: TEXT, rowH: 0.52, valign: "middle", border: { type: "none" } });
punktKort(s, 7.6, 1.4, 5.1, 1.6, "Styrke", `Eid av dagligvarebransjen (DLF og DMF). Omsetningen har vokst ${spenn(d.vekst_min, d.vekst_max)} i året, og driften har overskudd hvert år.`);
punktKort(s, 7.6, 3.15, 5.1, 1.6, "Svakhet", "Marginen er tynn og fallende. Gjelden og investeringene i lastbærere har økt, og ingen offentlig rating finnes.", AMBER);
punktKort(s, 7.6, 4.9, 5.1, 1.6, "Vurdering", "Lav risiko for mislighold. Risikoen sitter i fornyelsen i 2033, ikke i betalingsevnen.");
kilde(s, "Kilde: Regnskapsregisteret (revidert, Deloitte). Leie = driftsinntektene til Fugleåsen 7 AS. Leiedekning = (driftsresultat + leie) / leie.");

// 10 Neste steg
s = pres.addSlide({ masterName: "MORK", sectionTitle: "Leietaker og neste steg" });
s.addText("Før endelig bud", { placeholder: "title" });
s.addText([
  { text: "Få leiekontrakten: utløp, opsjoner, indeksering og eventuell garanti", options: { bullet: true, breakLine: true } },
  { text: "Bekreft leien og hva eierselskapets inntekter inneholder (solstrøm, viderefakturering)", options: { bullet: true, breakLine: true } },
  { text: "Teknisk due diligence og vedlikeholdsbehov frem mot 2033", options: { bullet: true, breakLine: true } },
  { text: "Tidlig dialog med NLP om forlengelse til markedsleie", options: { bullet: true } },
], { placeholder: "body", fontSize: 20, paraSpaceAfter: 8 });

pres.writeFile({ fileName: utFil }).then(() => console.log("ok", utFil));
