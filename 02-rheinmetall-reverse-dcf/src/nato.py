"""NATO 'Defence Expenditure of NATO Countries (2014-2026)' (published July 2026) tables, and the path of European NATO
members' equipment spending to 2035 under the June 2025 Hague commitment (3.5% of GDP core defence spending by 2035).

The 2026 edition is published as a scanned (image-only) PDF, so the tables are read with OCR (tesseract) and then
checked: every column used must add up to NATO's own 'NATO Europe and Canada' total (Table 2) and every value is
checked against a plausible range. Corrections of OCR misreads are listed explicitly in FIXES with the reason.

    python src/nato.py      (needs data/source/nato-def-exp-2026.pdf and tesseract)
"""
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / "data" / "source", ROOT / "data"
COLS = list(range(2014, 2025)) + ["2025e", "2026e"]
COUNTRIES = ["Albania", "Belgium", "Bulgaria", "Canada", "Croatia", "Czechia", "Denmark", "Estonia", "Finland", "France", "Germany",
             "Greece", "Hungary", "Italy", "Latvia", "Lithuania", "Luxembourg", "Montenegro", "Netherlands", "North Macedonia", "Norway",
             "Poland", "Portugal", "Romania", "Slovak Republic", "Slovenia", "Spain", "Sweden", "Türkiye", "United Kingdom",
             "United States"]
ALIASES = {"Rstonia": "Estonia", "Ttaly": "Italy", "Tarkiye": "Türkiye", "Tiirkiye": "Türkiye", "Turkiye": "Türkiye", "Slovenia*": "Slovenia"}
PAGES = {"t2": 6, "t3": 7, "t8a": 12}
ISO3 = {"Albania": "ALB", "Belgium": "BEL", "Bulgaria": "BGR", "Croatia": "HRV", "Czechia": "CZE", "Denmark": "DNK", "Estonia": "EST",
        "Finland": "FIN", "France": "FRA", "Germany": "DEU", "Greece": "GRC", "Hungary": "HUN", "Italy": "ITA", "Latvia": "LVA",
        "Lithuania": "LTU", "Luxembourg": "LUX", "Montenegro": "MNE", "Netherlands": "NLD", "North Macedonia": "MKD", "Norway": "NOR",
        "Poland": "POL", "Portugal": "PRT", "Romania": "ROU", "Slovak Republic": "SVK", "Slovenia": "SVN", "Spain": "ESP", "Sweden": "SWE",
        "Türkiye": "TUR", "United Kingdom": "GBR"}
EUROPE = [c for c in COUNTRIES if c not in ("Canada", "United States")]


def ocr_page(n):
    cache = OUT / "nato_ocr" / f"page-{n:02d}.txt"
    if not cache.exists():
        cache.parent.mkdir(exist_ok=True)
        png = cache.with_suffix("")
        subprocess.run(["pdftoppm", "-r", "300", "-png", "-f", str(n), "-l", str(n), "-singlefile", str(SRC / "nato-def-exp-2026.pdf"), str(png)], check=True)
        subprocess.run(["tesseract", str(png) + ".png", str(cache.with_suffix("")), "--psm", "6"], check=True, capture_output=True)
        Path(str(png) + ".png").unlink()
    return cache.read_text()


def clean(tok, pct):
    t = tok.replace("O", "0").replace("o", "0").rstrip(",.").replace(",", "" if not pct else ".")
    if pct:
        t = t.replace(",", ".")
        if re.fullmatch(r"\d{3}", t):          # dropped decimal point, e.g. '215' -> 2.15
            t = t[0] + "." + t[1:]
    try:
        return float(t)
    except ValueError:
        return np.nan


def parse(text, pct, stop=None):
    """Country rows of the first block of a table. Only the last three columns (2024, 2025e, 2026e) are kept: they are
    the ones used, and reading them from the right end of each line is robust to OCR noise in earlier columns."""
    rows = {}
    for line in text.splitlines():
        if stop and re.match(stop, line.strip()):
            break
        ln = line.strip()
        for a, b in ALIASES.items():
            if ln.startswith(a):
                ln = b + ln[len(a):]
        name = next((c for c in sorted(COUNTRIES + ["NATO Europe and Canada", "NATO Total"], key=len, reverse=True)
                     if ln.startswith(c)), None)
        if name is None or name in rows:
            continue
        toks = ln[len(name):].lstrip("*").split()
        if len(toks) < 3:
            continue
        rows[name] = [clean(t, pct) for t in toks[-3:]]
    return pd.DataFrame(rows, index=[2024, "2025e", "2026e"]).T


# OCR misreads found by the validation below; each is corrected from the row's own neighbours or the column total.
FIXES = {}


def tables():
    t2 = parse(ocr_page(PAGES["t2"]), pct=False, stop=r"^Constant 2021")
    t3 = parse(ocr_page(PAGES["t3"]), pct=True, stop=r"^Annual real change")
    t8 = parse(ocr_page(PAGES["t8a"]), pct=True, stop=r"^Personnel")
    for (tab, c, y), (v, why) in FIXES.items():
        {"t2": t2, "t3": t3, "t8a": t8}[tab].loc[c, y] = v
    return t2, t3, t8


def validate(t2, t3, t8):
    report = {}
    eu_can = [c for c in COUNTRIES if c != "United States"]
    for y in [2024, "2025e", "2026e"]:
        s = t2.loc[eu_can, y].sum()
        report[f"Table 2 sum {y}"] = (float(s), float(t2.loc["NATO Europe and Canada", y]))
    report["Table 3 range 2025e"] = (float(t3.loc[COUNTRIES, "2025e"].min()), float(t3.loc[COUNTRIES, "2025e"].max()))
    report["Table 8a range 2025e"] = (float(t8.loc[COUNTRIES, "2025e"].min()), float(t8.loc[COUNTRIES, "2025e"].max()))
    report["missing"] = {k: [c for c in COUNTRIES if c not in t.index or t.loc[c].isna().any()] for k, t in
                         {"t2": t2, "t3": t3, "t8a": t8}.items()}
    return report


def imf_gdp():
    d = json.load(open(OUT / "market" / "imf_weo_NGDPD_2026-10-07.json"))["values"]["NGDPD"]
    g = pd.DataFrame({c: {y: d[ISO3[c]].get(str(y)) for y in range(2024, 2032)} for c in EUROPE}).T.astype(float)
    cagr = (g[2031] / g[2026]) ** (1 / 5) - 1                 # extend 2032–2035 at the 2026–2031 IMF growth rate
    for y in range(2032, 2036):
        g[y] = g[y - 1] * (1 + cagr)
    return g                                                   # USD bn, current prices


def equipment_path(target=0.035, end=2035):
    """European NATO members' equipment spending, 2025–2035, USD m.
    2025 level = NATO core defence expenditure 2025e (Table 2, current USD) x equipment share 2025e (Table 8a).
    Growth = (share of GDP on a straight line from 2025e (Table 3) to 3.5% in 2035; members already above 3.5% stay at
    their 2025e share) x (IMF WEO nominal GDP growth). Equipment shares are held at their 2025e level."""
    t2, t3, t8 = tables()
    gdp = imf_gdp()
    out, check = {}, {}
    for c in EUROPE:
        s0 = t3.loc[c, "2025e"] / 100
        eq0 = t2.loc[c, "2025e"] * t8.loc[c, "2025e"] / 100
        row = {}
        for y in range(2025, end + 1):
            s = max(s0, s0 + (target - s0) * (y - 2025) / (end - 2025))
            row[y] = eq0 * (s / s0) * (gdp.loc[c, y] / gdp.loc[c, 2025])
        out[c] = row
        check[c] = {"NATO share of GDP 2025e": s0, "Table 2 / IMF GDP 2025": t2.loc[c, "2025e"] / (gdp.loc[c, 2025] * 1000)}
    P = pd.DataFrame(out).T
    C = pd.DataFrame(check).T
    C["gap (pp)"] = (C.iloc[:, 1] - C.iloc[:, 0]) * 100
    return P, C


if __name__ == "__main__":
    t2, t3, t8 = tables()
    print(json.dumps(validate(t2, t3, t8), indent=1, default=str))
    P, C = equipment_path()
    print(C.round(4).sort_values("gap (pp)"))
    tot = P.sum()
    print((tot / 1000).round(1))
