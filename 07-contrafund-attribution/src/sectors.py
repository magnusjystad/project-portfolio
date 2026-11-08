"""yfinance sector field for every priced holding (cached, resumable)."""
import json
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
cache = ROOT / "data" / "sectors_cache.json"
known = json.loads(cache.read_text()) if cache.exists() else {}
chosen = json.load(open(ROOT / "data" / "quarter_end_prices_usd.json"))
for isin, t in chosen.items():
    if isin in known and known[isin].get("sector"):
        continue
    for attempt in range(4):
        try:
            info = yf.Ticker(t).info
            known[isin] = {"ticker": t, "sector": info.get("sector"), "industry": info.get("industry"),
                           "quoteType": info.get("quoteType")}
            break
        except Exception as e:
            known[isin] = {"ticker": t, "sector": None, "error": repr(e)[:120]}
            time.sleep(30 * (attempt + 1))
    cache.write_text(json.dumps(known, indent=0))
    time.sleep(0.6)
s = pd.DataFrame(known).T
s.index.name = "isin"
s.to_csv(ROOT / "data" / "sectors.csv")
print("done", len(s), s["sector"].isna().sum(), "missing")
