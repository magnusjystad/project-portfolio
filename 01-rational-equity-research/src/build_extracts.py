"""Rebuilds the three extracted data files from the annual-report PDFs in data/source/ (not redistributed; download
them from rational-online.com, Investor Relations > Publications).

    python src/build_extracts.py

- data/extract_raw.csv            income statement, balance sheet and cash flow 2016–2025 (kEUR), src/extract.py
- data/extract_regions.csv        sales by customer region 2016–2025 (kEUR)
- data/extract_product_groups.csv iVario / iCombi sales 2016–2025 (kEUR)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT)]
import pandas as pd
import pdfplumber

from src import extract

SRC, DATA = ROOT / "data" / "source", ROOT / "data"
YEARS = range(2016, 2026)
N = r"(\d{1,3}(?:,\d{3})+)"
REG = {"Germany": rf"(?<!excluding )(?<!excl\. )Germany\s+{N}\s+\d+\s+{N}\s+\d+",
       "Europe ex-Germany": rf"\(excl(?:uding|\.)\s*Germany\)\s+{N}\s+\d+\s+{N}",
       "North America": rf"North America\s+{N}\s+\d+\s+{N}", "Latin America": rf"Latin America\s+{N}\s+\d+\s+{N}",
       "Asia": rf"Asia\s+{N}\s+\d+\s+{N}", "Rest of world": rf"Rest of the world\s*\*?\s+{N}\s+\d+\s+{N}"}
RCOLS = list(REG)


def statements():
    rows = {}
    for y in YEARS:
        r = extract.extract_year(SRC / f"AR_{y}.pdf")
        r.pop("_pages")
        rows[y] = r
    D = pd.DataFrame(rows)
    D.to_csv(DATA / "extract_raw.csv")
    return D


def _region_table(page, group):
    for tt in [page.extract_text(), page.crop((0, 0, page.width / 2, page.height)).extract_text(),
               page.crop((page.width / 2, 0, page.width, page.height)).extract_text()]:
        tt = re.sub(r"\s*\|\s*", " ", (tt or "").replace("\n", " "))
        vals = {k: re.search(p, tt) for k, p in REG.items()}
        if all(vals.values()):
            return {k: float(m.group(group).replace(",", "")) for k, m in vals.items()}
    return None


def regions(raw):
    res = {}
    for y in YEARS:
        with pdfplumber.open(SRC / f"AR_{y}.pdf") as pdf:
            for i, p in enumerate(pdf.pages):
                t = p.extract_text() or ""
                if "Rest of the world" in t and "Latin America" in t and re.search(r"[Rr]egional breakdown of sales revenues", t):
                    v = _region_table(p, 1)
                    if v:
                        res[y] = {**v, "_page": i + 1}
                        break
    # 2022: the 2022 report's table does not parse; use the prior-year column of the 2023 report
    with pdfplumber.open(SRC / "AR_2023.pdf") as pdf:
        p = pdf.pages[int(res[2023]["_page"]) - 1]
        res[2022] = {**_region_table(p, 2), "_page": f"prior-year column, AR 2023 p{p.page_number}"}
    # 2021: the 2021 report prints the table in a layout pdfplumber's text order breaks; the values below were read
    # from AR 2021 p49 by word position and are checked against total sales below
    res[2021] = {"Germany": 102528.0, "Europe ex-Germany": 336757.0, "North America": 140415.0, "Latin America": 35452.0,
                 "Asia": 122777.0, "Rest of world": 41805.0, "_page": "AR 2021 p49 (word-position extraction)"}
    R = pd.DataFrame(res).T.sort_index()
    R["Sum"] = R[RCOLS].astype(float).sum(axis=1)
    R["Sales (IS)"] = [raw.loc["Sales revenues", y] for y in R.index]
    assert (R["Sum"] == R["Sales (IS)"]).all(), "regions do not sum to sales"
    R.to_csv(DATA / "extract_regions.csv")
    return R


def product_groups(raw):
    out = {}
    for y in [2016, 2017, 2018]:          # FRIMA segment (VarioCookingCenter) external sales
        with pdfplumber.open(SRC / f"AR_{y}.pdf") as pdf:
            for i, p in enumerate(pdf.pages):
                t = p.extract_text() or ""
                m = re.search(rf"{y} in kEUR.*?External sales revenues\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)", t, re.S)
                if m and "FRIMA" in t:
                    out[y] = {"iVario": float(m.group(2).replace(",", "")), "src": f"AR {y} p{i + 1}"}
                    break
    # 2019–2025: sales by product group, note 1 of each report (transcribed with page references)
    notes = {2019: (74507, "AR 2019 p83 (note 1: VarioCookingCenter product group)"), 2020: (68984, "AR 2020 p45 (note 1)"),
             2021: (81351, "AR 2021 p49 (note 1)"), 2022: (127738, "AR 2022 p49 (note 1)"), 2023: (118139, "AR 2023 p50 (note 1)"),
             2024: (137429, "AR 2024 p51 (note 1)"), 2025: (151203, "AR 2025 p117 (note 1)")}
    for y, (v, s) in notes.items():
        out[y] = {"iVario": float(v), "src": s}
    P = pd.DataFrame(out).T.sort_index(); P.index.name = "year"
    P["Total sales"] = [raw.loc["Sales revenues", y] for y in P.index]
    P["iCombi (= total - iVario)"] = P["Total sales"] - P["iVario"].astype(float)
    P.to_csv(DATA / "extract_product_groups.csv")
    return P


if __name__ == "__main__":
    raw = statements()
    regions(raw)
    product_groups(raw)
    print("rebuilt extract_raw.csv, extract_regions.csv, extract_product_groups.csv")
