"""Market inputs for the Rheinmetall reverse DCF (saved to data/market/; each file is downloaded once).

    python src/inputs.py

- Daily prices (yfinance): RHM.DE, STOXX Europe 600 (^STOXX) and the five peers.
- 10-year Bund yield (Deutsche Bundesbank) and Damodaran's implied ERP: same files and method as Project 1.
- Rheinmetall 3.375% 2026/2031 bond (XS3344481935): last price on Börse Frankfurt, 7 Oct 2026 (saved API response and
  page quote in data/market/); the yield to maturity is computed in src/model.py.
"""
from pathlib import Path

import pandas as pd
import yfinance as yf

OUT = Path(__file__).resolve().parents[1] / "data" / "market"
TICKERS = ["RHM.DE", "^STOXX", "BA.L", "HO.PA", "LDO.MI", "SAAB-B.ST", "KOG.OL"]


def prices():
    f = OUT / "prices_daily.csv"
    if not f.exists():
        d = yf.download(TICKERS, start="2016-01-01", end="2026-10-08", auto_adjust=False, progress=False, threads=False)
        d["Close"][TICKERS].to_csv(f)
        d["Adj Close"][TICKERS].to_csv(OUT / "prices_adj_daily.csv")
    return pd.read_csv(f, index_col=0, parse_dates=True)


if __name__ == "__main__":
    print(prices().tail(3))
