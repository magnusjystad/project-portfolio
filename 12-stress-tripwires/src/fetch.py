"""Downloads every market input into data/raw/. Re-run before each weekly check.

    python src/fetch.py
"""
from pathlib import Path

import requests
import yfinance as yf

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
FRED = ["SOFR", "IORB", "IOER", "RPONTSYD", "BAMLH0A0HYM2", "SWPT", "DEXJPUS", "VIXCLS", "DGS10", "DGS30", "DCOILBRENTEU", "EFFR"]
MOF = {"mof_jgb_historical.csv": "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv",
       "mof_jgb_current_month.csv": "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv"}
CFTC_YEARS = range(2010, 2027)   # Traders in Financial Futures, futures only, one zip per year


def get(url, path):
    r = requests.get(url, timeout=120, headers={"User-Agent": "Investment research portfolio"})
    r.raise_for_status()
    path.write_bytes(r.content)


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for s in FRED:
        get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}", RAW / f"fred_{s}.csv")
    for f, u in MOF.items():
        get(u, RAW / f)
    for y in CFTC_YEARS:
        get(f"https://www.cftc.gov/files/dea/history/fut_fin_txt_{y}.zip", RAW / f"cftc_fin_{y}.zip")
    for t, f in [("^MOVE", "yahoo_MOVE.csv"), ("BZ=F", "yahoo_BZ_F.csv")]:
        h = yf.download(t, start="2000-01-01", progress=False, auto_adjust=False)
        h.columns = h.columns.get_level_values(0)
        h[["Close"]].to_csv(RAW / f)
    print("downloaded to", RAW)
