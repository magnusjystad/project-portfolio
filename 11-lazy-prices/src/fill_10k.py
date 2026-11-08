"""Second pass: fetch 10-Ks the first pass missed, and pull MD&A / risk factors from Exhibit 13 when the
10-K incorporates them by reference (common for banks and some industrials)."""
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
from edgar import Company, set_identity
from edgar.company_reports import TenK

set_identity("Investment research portfolio magjys@hotmail.com")
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw_10k"
log = open(ROOT / "data" / "fill_log.txt", "a")
cons = pd.read_csv(ROOT / "data" / "sp100_constituents_wikipedia.csv")
tickers = [t for t in cons["Symbol"] if t != "GOOG"]
W, N = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (0, 1)
tickers = tickers[W::N]

MDA = re.compile(r"management[’'`]?s\s+discussion\s+and\s+analysis", re.I)
MDA_END = re.compile(r"report\s+of\s+independent\s+registered\s+public\s+accounting\s+firm|management[’'`]?s\s+report\s+on\s+internal\s+control|consolidated\s+statements?\s+of\s+(income|operations|earnings)\b", re.I)
RF = re.compile(r"\brisk\s+factors\b", re.I)


def fiscal_year(f):
    p = str(f.period_of_report or "")
    if re.match(r"\d{4}-\d\d-\d\d", p):
        return int(p[:4]), p
    d = pd.Timestamp(str(f.filing_date)) - pd.DateOffset(months=3)
    return d.year, f"{d.year}-12-31?"


TOC_NEAR = re.compile(r"report\s+of\s+independent|consolidated\s+(balance|statements?)|selected\s+financial\s+data|"
                      r"five-year|stockholder\s+information|shareholder\s+information|\bpage\b", re.I)


def section_from_exhibit(text, start_re, end_re, min_len=10000):
    """Section text from Exhibit 13. Skip heading matches that look like a table of contents (another
    section title within the next 400 characters), start at the first remaining match and stop at the
    first end marker at least `min_len` characters later."""
    for m in start_re.finditer(text):
        if TOC_NEAR.search(text, m.end(), m.end() + 400):
            continue
        e = end_re.search(text, m.end() + min_len) if end_re is not None else None
        seg = text[m.start(): e.start() if e else min(len(text), m.start() + 300_000)]
        if len(seg) >= min_len:
            return seg
    return ""


def ex13_text(f):
    for a in f.attachments:
        dt = (a.document_type or "").upper()
        if dt.startswith("EX-13"):
            try:
                return a.text() or ""
            except Exception:
                return ""
    return ""


for tk in tickers:
    try:
        fs = [f for f in Company(tk.replace(".", "-")).get_filings(form="10-K") if f.form == "10-K"]
    except Exception as e:
        print(tk, "company error", repr(e)[:150], file=log, flush=True)
        continue
    have = {p.name.split("_")[2].replace(".json", ""): p for p in RAW.glob(f"{tk}_*.json")}
    for f in fs:
        fy, per = fiscal_year(f)
        if fy < 2011 or fy > 2025:
            continue
        out = have.get(f.accession_no) or RAW / f"{tk}_{per.replace('?', '')}_{f.accession_no}.json"
        rec = json.loads(out.read_text()) if out.exists() else None
        try:
            if rec is None:
                o = TenK(f)
                rec = {"ticker": tk, "cik": None, "accession": f.accession_no, "filing_date": str(f.filing_date),
                       "period": per.replace("?", ""), "item1a": o["Item 1A"] or "", "item7": o["Item 7"] or ""}
                print(tk, per, "fetched", len(rec["item1a"]), len(rec["item7"]), file=log, flush=True)
            changed = False
            if len(rec.get("item7", "")) < 2000 and rec.get("ex13_version") != 2:
                ex = ex13_text(f)
                rec["ex13_raw_len"] = len(ex)
                rec["item7_ex13"] = section_from_exhibit(ex, MDA, MDA_END) if ex else ""
                changed = True
                print(tk, per, "ex13 mda", len(rec["item7_ex13"]), file=log, flush=True)
            if len(rec.get("item1a", "")) < 2000 and rec.get("ex13_version") != 2:
                ex = ex13_text(f)
                rec["item1a_ex13"] = section_from_exhibit(ex, RF, MDA) if ex else ""
                changed = True
                print(tk, per, "ex13 rf", len(rec["item1a_ex13"]), file=log, flush=True)
            if changed:
                rec["ex13_version"] = 2
            if changed or not out.exists():
                out.write_text(json.dumps(rec))
            time.sleep(0.3)
        except Exception as e:
            print(tk, per, "error", repr(e)[:150], file=log, flush=True)
            time.sleep(60 if "429" in repr(e) else 3)
print("DONE", file=log, flush=True)
