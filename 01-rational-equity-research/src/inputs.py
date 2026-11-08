"""Market inputs for the valuation, saved to data/market/ (each file is downloaded once).

    python src/inputs.py

- 10-year German Bund yield, daily (Deutsche Bundesbank, series BBSIS D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A)
- Euro-area AAA 10-year spot yield, daily (ECB Data Portal, YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y), as a cross-check
- Damodaran implied equity risk premium by month (ERPbymonth.xlsx)
- Daily prices from yfinance: RAA.DE, STOXX Europe 600 (^STOXX), MIDD, EPRO-B.ST, 6465.T and EUR FX rates
"""
import io
import sys
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "market"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (research; magjys@hotmail.com)"}
PUB = "2026-10-07"   # publication date


def bund():
    f = OUT / "bund10y_bundesbank_daily.csv"
    if not f.exists():
        url = ("https://api.statistiken.bundesbank.de/rest/download/BBSIS/"
               "D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A?format=csv&lang=en")
        r = requests.get(url, headers=UA, timeout=60); r.raise_for_status()
        f.write_bytes(r.content)
    raw = f.read_text(encoding="utf-8-sig").splitlines()
    rows = [l.split(",") for l in raw if l[:4].isdigit()]
    s = pd.Series({pd.Timestamp(r[0]): pd.to_numeric(r[1], errors="coerce") for r in rows}).dropna() / 100
    return s.sort_index()


def ecb_aaa():
    f = OUT / "ecb_aaa_10y_daily.csv"
    if not f.exists():
        url = "https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y?startPeriod=2026-01-01&format=csvdata"
        r = requests.get(url, headers=UA, timeout=60); r.raise_for_status()
        f.write_bytes(r.content)
    d = pd.read_csv(f)
    return pd.Series(d["OBS_VALUE"].values / 100, index=pd.to_datetime(d["TIME_PERIOD"])).sort_index()


def damodaran():
    f = OUT / "damodaran_ERPbymonth.xlsx"
    if not f.exists():
        r = requests.get("https://pages.stern.nyu.edu/~adamodar/pc/implprem/ERPbymonth.xlsx", headers=UA, timeout=60)
        r.raise_for_status(); f.write_bytes(r.content)
    return pd.read_excel(f, header=None)


def prices():
    f = OUT / "prices_daily.csv"
    if not f.exists():
        tk = ["RAA.DE", "^STOXX", "MIDD", "EPRO-B.ST", "6465.T", "EURUSD=X", "EURSEK=X", "EURJPY=X"]
        d = yf.download(tk, start="2016-01-01", end="2026-10-08", auto_adjust=False, progress=False, threads=False)
        d["Close"][tk].to_csv(f)
        d["Adj Close"][tk].to_csv(OUT / "prices_adj_daily.csv")
    return pd.read_csv(f, index_col=0, parse_dates=True)


if __name__ == "__main__":
    b, e = bund(), ecb_aaa()
    print("Bund 10y latest:", b.index[-1].date(), f"{b.iloc[-1]:.4%}", "| ECB AAA 10y latest:", e.index[-1].date(), f"{e.iloc[-1]:.4%}")
    x = damodaran(); print(x.head(8).to_string()[:1200]); print(x.tail(4).to_string()[:1200])
    p = prices(); print(p.tail(4))
    sys.exit(0)
