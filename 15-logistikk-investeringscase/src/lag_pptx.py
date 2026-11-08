"""Lager PowerPoint-versjonen av memoet (report/investeringscase_fugleasen7.pptx). Tallene hentes fra Python-modellen og
skrives til en midlertidig JSON-fil som src/lag_pptx.js (pptxgenjs) bygger presentasjonen fra.

    npm install pptxgenjs@3.12.0      # én gang; eller sett NODE_PATH til en mappe med pptxgenjs
    python src/lag_pptx.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import modell as Mo  # noqa: E402

D = ROOT / "data"
X = Mo.run(); R = X["R"]; M = Mo.M; A = Mo.ANTAGELSER
nlp = pd.read_csv(D / "leietaker_regnskap.csv", index_col=0)
f7 = pd.read_csv(D / "fugleasen7_as_regnskap.csv", index_col=0)
tr = pd.read_csv(D / "transaksjoner.csv")
leie = f7["Driftsinntekter"]
cf = R["cf"]
yrs = [int(y) for y in cf.index[:-1]]
data = {
    "pris": X["pris"], "maks_bud": X["maks_bud"], "maks_lav": Mo.resultat(None, markedsleie=M["markedsleie_langhus_lav"])["maks_bud"],
    "irr": R["irr"], "irr_bel": R["irr_belant"], "mult": R["multippel"], "mult_bel": R["multippel_belant"],
    "startyield": R["netto_startyield"], "brutto_yield": float(cf.iloc[0]["Brutto leie"] / X["pris"]), "pris_m2": R["pris_m2"],
    "exit": R["exit"], "icr": R["rentedekning_ar1"], "leie26_m2": X["leie26_m2"], "areal": M["areal"],
    "vekst_min": float(nlp["Driftsinntekter"].pct_change().min()), "vekst_max": float(nlp["Driftsinntekter"].pct_change().max()),
    "rev_andel": 1 - X["scenarier"].loc["NLP fornyer til dagens leie", "Maks bud"] / X["maks_bud"],
    "A": A, "M": M,
    "aar": yrs, "noi": [float(v) for v in cf.loc[yrs, "Netto driftsinntekt"]],
    "noi_kontrakt": [float(v) for v in cf.loc[yrs, "Kontraktsleie (100 %)"] * (1 - A["eierkost"])],
    "grid": {"leie": Mo.LEIEGRID, "yield": Mo.YIELDGRID, "irr": X["grid"].values.tolist()},
    "scen": [{"navn": k, "irr": float(v["IRR"]), "irr_bel": float(v["IRR belånt"]), "maks": float(v["Maks bud"])}
             for k, v in X["scenarier"].iterrows()],
    "comps": [{"navn": n, "aar": str(d)[:4], "kjoper": k, "pris": p, "areal": a, "kr_m2": p * 1e6 / a,
               "yield": (l / p if pd.notna(l) else None)}
              for n, d, k, p, a, l in zip(["Project Athena (14 eiendommer, bl.a. Langhus)", "Urban Partners-porteføljen (Vestby, Moss)",
                                           "Ahlsell sentrallager, Eidsvoll", "World Seafood Center, Gardermoen"],
                                          tr["Dato"], tr["Kjøper"], tr["Pris (NOK mill.)"], tr["Areal (m2)"], tr["Årlig leie (NOK mill.)"])
              if pd.notna(p)],
    "nlp": {str(y): {"oms": float(nlp.loc[y, "Driftsinntekter"]), "margin": float(nlp.loc[y, "Driftsresultat"] / nlp.loc[y, "Driftsinntekter"]),
                     "ek": float(nlp.loc[y, "Egenkapital"] / nlp.loc[y, "Sum eiendeler"]),
                     "rd": float(nlp.loc[y, "Driftsresultat"] / nlp.loc[y, "Finanskostnader"]),
                     "leie_andel": float(leie.loc[y] / nlp.loc[y, "Driftsinntekter"]),
                     "leiedekning": float((nlp.loc[y, "Driftsresultat"] + leie.loc[y]) / leie.loc[y]),
                     "kontanter_leie": float(nlp.loc[y, "Bankinnskudd og kontanter"] / leie.loc[y])} for y in nlp.index},
}

if __name__ == "__main__":
    tmp = Path(tempfile.mkdtemp()) / "deck.json"
    tmp.write_text(json.dumps(data, ensure_ascii=False, default=float))
    out = ROOT / "report" / "investeringscase_fugleasen7.pptx"
    subprocess.run(["node", str(ROOT / "src" / "lag_pptx.js"), str(tmp), str(out)], check=True, env={**os.environ})
    print("skrev", out)
