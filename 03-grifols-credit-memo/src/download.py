"""Downloads the inputs of this project into data/source/ and data/market/.

SEC filings are located through EDGAR's submissions API: each file below is either the primary document of a Grifols filing
(6-K results releases, the 20-F) or an exhibit to the 20-F of the year in its name (the indentures).

    python src/download.py            # download everything
    python src/download.py --resolve  # only print the URLs

Bond prices (Börse Frankfurt, finanzen.net) and the Grifols ratings page are JavaScript-rendered; the snapshots taken on
7 Oct 2026 are kept in data/market/ and data/source/ (see data/market/bond_quotes.csv for the URLs).
"""
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
SRC, MKT = ROOT / "data" / "source", ROOT / "data" / "market"
CIK = 1438569
UA = {"User-Agent": "Investment research portfolio magjys@hotmail.com"}

PRIMARY = {  # local name: primary document of a Grifols filing
    "fy_a20-11032_16k.htm": "FY2019 results (6-K, Feb 2020)",
    "fy_tm217998d1_6k.htm": "FY2020 results (6-K, Feb 2021)",
    "fy_tm227653d1_6k.htm": "FY2021 results (6-K, Feb 2022)", "fy_tm227653d2_6k.htm": "FY2021 results, part 2",
    "fy_tm237969d1_6k.htm": "FY2022 results (6-K, Feb 2023)",
    "fy_tm247376d2_6k.htm": "FY2023 results (6-K, Feb 2024)", "fy_tm247743d4_6k.htm": "FY2023 results presentation",
    "fy_tm257688d1_6k.htm": "FY2024 results (6-K, Feb 2025)", "fy_tm257688d2_6k.htm": "FY2024 results presentation",
    "fy_tm267368d1_6k.htm": "FY2025 audited accounts (6-K, Feb 2026)", "fy_tm267368d2_6k.htm": "FY2025 results presentation",
    "6k_tm2621481d1_6k.htm": "H1 2026 interim report and results (6-K, Jul 2026)",
    "6k_tm2611793d1_6k.htm": "2026 6-K", "6k_tm2613942d1_6k.htm": "2026 6-K", "6k_tm2614775d1_6k.htm": "2026 6-K",
    "6k_tm2618302d1_6k.htm": "2026 6-K", "6k_tm2618474d1_6k.htm": "2026 6-K", "6k_tm2621687d1_6k.htm": "2026 6-K",
    "6k_tm262646d1_6k.htm": "2026 6-K", "6k_tm269714d1_6k.htm": "2026 6-K",
    "gotham_tm242492d1_6k.htm": "Grifols response to Gotham (Jan 2024)", "gotham_tm242492d2_6k.htm": "Gotham response, part 2",
    "gotham_tm242492d3_6k.htm": "Gotham response, part 3", "gotham_tm242492d4_6k.htm": "Gotham response, part 4",
    "gotham_tm243345d1_6k.htm": "Gotham response (Jan 2024)", "gotham_tm244285d1_6k.htm": "Gotham response (Jan 2024)",
    "grfs-20251231x20f.htm": "20-F 2025",
}
EXHIBITS = ["grfs-20241231xex2d14.htm", "grfs-20241231xex2d15.htm", "grfs-20241231xex2d16.htm",  # 2030 notes indentures
            "grfs-20211231xex2d6.htm", "grfs-20211231xex2d8.htm", "grfs-20211231xex2d9.htm",     # 2028 notes indenture
            "grfs-20251231xex2d9.htm", "grfs-20251231xex2d12.htm", "grfs-20251231xex2d13.htm", "grfs-20251231xex2d15.htm"]
OTHER = {
    "grifols_companyfacts.json": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK:010d}.json",
    "sp_2024_annual_global_corporate_default_study.pdf":
        "https://www.spglobal.com/ratings/en/research/articles/250327-default-transition-and-recovery-2024-annual-global-corporate-"
        "default-and-rating-transition-study-13432069 (PDF download link on the page)",
}
MARKET = {
    "fred_BAMLHE00EHYIOAS.csv": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLHE00EHYIOAS",
    "fred_SOFR.csv": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SOFR",
    "fred_DEXUSEU.csv": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXUSEU",
    "fred_IR3TIB01EZM156N.csv": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=IR3TIB01EZM156N",
    "ecb_euribor3m.csv": "https://data-api.ecb.europa.eu/service/data/FM/M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA?format=csvdata",
    **{f"bund_svensson_{m}.csv": ("https://api.statistiken.bundesbank.de/rest/download/BBSIS/"
                                  f"D.I.ZST.ZI.EUR.S1311.B.A604.{m}.R.A.A._Z._Z.A?format=csv&lang=en")
       for m in ["R01XX", "R02XX", "R03XX", "R04XX"]},
}


def filings():
    """(accession, primaryDocument, form, reportDate) for every Grifols filing."""
    j = requests.get(f"https://data.sec.gov/submissions/CIK{CIK:010d}.json", headers=UA, timeout=60).json()
    blocks = [j["filings"]["recent"]] + [requests.get(f"https://data.sec.gov/submissions/{f['name']}", headers=UA, timeout=60).json()
                                         for f in j["filings"].get("files", [])]
    out = []
    for b in blocks:
        out += list(zip(b["accessionNumber"], b["primaryDocument"], b["form"], b["reportDate"]))
    return out


def resolve():
    F = filings()
    urls = {}
    base = f"https://www.sec.gov/Archives/edgar/data/{CIK}"
    for local in PRIMARY:
        doc = local.split("_", 1)[1] if local.startswith(("fy_", "6k_", "gotham_")) else local
        hit = [a for a, d, *_ in F if d == doc]
        urls[local] = f"{base}/{hit[0].replace('-', '')}/{doc}" if hit else None
    for ex in EXHIBITS:
        year = ex[5:9]
        hit = [a for a, d, form, rd in F if form == "20-F" and rd.startswith(year)]
        urls[ex] = f"{base}/{hit[0].replace('-', '')}/{ex}" if hit else None
    return urls


if __name__ == "__main__":
    urls = resolve()
    if "--resolve" in sys.argv:
        print(json.dumps(urls | OTHER | MARKET, indent=1))
        sys.exit(0 if all(urls.values()) else 1)
    SRC.mkdir(parents=True, exist_ok=True); MKT.mkdir(parents=True, exist_ok=True)
    for local, url in urls.items():
        if url is None:
            print("not found on EDGAR:", local); continue
        (SRC / local).write_bytes(requests.get(url, headers=UA, timeout=120).content); time.sleep(0.2)
    (SRC / "grifols_companyfacts.json").write_bytes(requests.get(OTHER["grifols_companyfacts.json"], headers=UA, timeout=120).content)
    for local, url in MARKET.items():
        (MKT / local).write_bytes(requests.get(url, timeout=120).content)
    print("done; download the S&P study PDF by hand from:", OTHER["sp_2024_annual_global_corporate_default_study.pdf"])
