"""Downloads the raw inputs for Project 9 into data/ (each step is skipped if its file already exists).

    python src/collect.py

1. Form N-PORT holdings for the three funds and ACWI (SEC EDGAR, located by series ID).
2. iShares MSCI ACWI holdings files (GICS sectors) from ishares.com.
3. Summary prospectuses (Form 497K) as plain text from EDGAR.
4. GICS sector / location for every fund holding (src/classify.py).
Prices and Fama-French factors are downloaded and cached by the notebook itself.
"""
import json
import re
import sys
import time
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import pandas as pd
import requests

from src import acwi as A
from src import classify as C
from src import nport

DATA = ROOT / "data"
UA = {"User-Agent": "Investment research portfolio magjys@hotmail.com"}
SERIES = {"ANWPX": (71516, "S000009613"), "DODWX": (29440, "S000022057"),
          "PRGSX": (313212, "S000001497"), "ACWI": (1100663, "S000021461")}
DATES = {"ANWPX": ["2026-06-30"], "DODWX": ["2026-06-30"], "PRGSX": ["2026-07-31"], "ACWI": ["2026-04-30", "2026-07-31"]}
ISHARES = ("https://www.ishares.com/us/products/239600/ishares-msci-acwi-etf/varnish-api/blk-one01-product-data/"
           "product-data/api/v1/get-fund-document?appType=PRODUCT_PAGE&appSubType=ISHARES&targetSite=us-ishares"
           "&locale=en_US&portfolioId=239600&userType=individual&asOfDate={d}&component=holdings")
PROSPECTUS = {"ANWPX": [(71516, "0000051931-20-001261"), (71516, "0000051931-25-001323")],
              "DODWX": [(29440, "0001193125-21-144172"), (29440, "0001193125-26-197958")],
              "PRGSX": [(313212, "0001741773-21-000411"), (313212, "0001741773-21-002140"),
                        (313212, "0001741773-21-003561"), (313212, "0001999371-25-021053")],
              "ACWI": [(1100663, "0001193125-25-302112")]}


def get_nport():
    meta_f = DATA / "nport" / "filings.json"
    meta = json.loads(meta_f.read_text()) if meta_f.exists() else {}
    for lab, (cik, sid) in SERIES.items():
        _, m = nport.fetch_by_series(cik, sid, DATES[lab], DATA / "nport", lab)
        if m:
            latest = max(m)
            meta[lab] = {k: m[latest][k] for k in ["series_name", "series_id", "rep_pd_date", "total_assets", "net_assets", "accession"]}
    meta_f.write_text(json.dumps(meta, indent=1))


def get_ishares():
    for d in ["20260630", "20260731"]:
        f = DATA / f"acwi_holdings_{d}.raw"
        if not f.exists():
            r = requests.get(ISHARES.format(d=d), headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
            r.raise_for_status()
            f.write_text(r.text)


def get_prospectuses():
    out = DATA / "prospectus"; out.mkdir(exist_ok=True)
    for lab, items in PROSPECTUS.items():
        for cik, acc in items:
            f = out / f"{lab}_{acc}.txt"
            if f.exists():
                continue
            base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}"
            idx = requests.get(f"{base}/{acc}-index.htm", headers=UA, timeout=60).text
            doc = re.search(r'href="(/Archives/edgar/data/[^"]+\.htm)"', idx).group(1)
            html = requests.get("https://www.sec.gov" + doc, headers=UA, timeout=60).text
            text = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html)))
            f.write_text(text)
            time.sleep(0.3)


def get_sectors():
    ish = {"2026-06-30": A.read_ishares(DATA / "acwi_holdings_20260630.raw"),
           "2026-07-31": A.read_ishares(DATA / "acwi_holdings_20260731.raw")}
    for lab in ["ANWPX", "DODWX", "PRGSX"]:
        f = DATA / f"{lab}_holdings_classified.csv"
        if f.exists():
            continue
        d = DATES[lab][0]
        h = pd.read_csv(DATA / "nport" / f"{lab}_{d}.csv")
        h = h[h["asset_cat"].isin(["EC", "EP"])].copy()
        C.classify(h, ish[d], DATA / "openfigi_map.json", DATA / "yf_sector_cache.json").to_csv(f, index=False)


if __name__ == "__main__":
    get_nport(); get_ishares(); get_prospectuses(); get_sectors()
    print("inputs in", DATA)
