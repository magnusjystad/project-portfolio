"""Download Item 1A and Item 7 of every 10-K (fiscal years 2011-2025) for the current S&P 100.
Raw text is cached in data/raw_10k/ (not committed); one JSON file per filing."""
import json
import sys
import time
from pathlib import Path

import pandas as pd
from edgar import Company, set_identity
from edgar.company_reports import TenK

set_identity("Investment research portfolio magjys@hotmail.com")
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw_10k"
RAW.mkdir(parents=True, exist_ok=True)
cons = pd.read_csv(ROOT / "data" / "sp100_constituents_wikipedia.csv")
tickers = [t for t in cons["Symbol"] if t != "GOOG"]          # GOOG and GOOGL are the same filer
W, N = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (0, 1)   # worker index, number of workers
tickers = tickers[W::N]
log = open(ROOT / "data" / "fetch_log.txt", "a")

for tk in tickers:
    try:
        c = Company(tk.replace(".", "-"))
        fs = c.get_filings(form="10-K")
    except Exception as e:
        print(tk, "company error", e, file=log, flush=True)
        continue
    for f in fs:
        per = str(f.period_of_report)
        yr = int(per[:4])
        if yr < 2011 or yr > 2025:
            continue
        out = RAW / f"{tk}_{per}_{f.accession_no}.json"
        if out.exists():
            continue
        for attempt in range(3):
            try:
                o = TenK(f)
                rec = {"ticker": tk, "cik": c.cik, "accession": f.accession_no, "filing_date": str(f.filing_date),
                       "period": per, "item1a": o["Item 1A"] or "", "item7": o["Item 7"] or ""}
                out.write_text(json.dumps(rec))
                print(tk, per, len(rec["item1a"]), len(rec["item7"]), file=log, flush=True)
                time.sleep(0.4)
                break
            except Exception as e:
                print(tk, per, "error", attempt, repr(e)[:200], file=log, flush=True)
                time.sleep(90 if "429" in repr(e) or "Rate" in repr(e) else 5)
print("DONE", file=log, flush=True)
