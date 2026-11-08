"""Third pass for filings whose Item 1A or Item 7 is short or empty after the edgartools parse:
(a) regex extraction from the full 10-K text; (b) cache the raw Exhibit 13 text when the 10-K incorporates
the section by reference. Only the original 10-K for each (ticker, fiscal year) is processed."""
import glob
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
from edgar import find, set_identity

set_identity("Investment research portfolio magjys@hotmail.com")
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw_10k"
EX13 = RAW / "ex13"
EX13.mkdir(exist_ok=True)
log = open(ROOT / "data" / "repair_log.txt", "a")
W, N = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (0, 1)

ITEM = {"item1a": (r"item\s*1a\.?\s*[\-–—:]?\s*risk\s+factors", r"item\s*1b\.?|item\s*2\.?\s*[\-–—:]?\s*properties"),
        "item7": (r"item\s*7\.?\s*[\-–—:]?\s*management[’'`]?s\s+discussion", r"item\s*7a\.?|item\s*8\.?\s*[\-–—:]?\s*financial\s+statements")}


def longest_span(text, start_pat, end_pat):
    best = ""
    for m in re.finditer(start_pat, text, re.I):
        e = re.search(end_pat, text[m.end():], re.I)
        seg = text[m.start(): m.end() + (e.start() if e else 0)] if e else ""
        if len(seg) > len(best):
            best = seg
    return best


recs = []
for f in glob.glob(str(RAW / "*.json")):
    d = json.load(open(f))
    recs.append((f, d["ticker"], d["period"][:4], d["filing_date"], len(d.get("item1a", "")), len(d.get("item7", "")), d["accession"]))
df = pd.DataFrame(recs, columns=["file", "ticker", "fy", "filed", "n1a", "n7", "acc"]).sort_values(["ticker", "fy", "filed"])
orig = df.groupby(["ticker", "fy"]).first().reset_index()
todo = orig[(orig.n1a < 2000) | (orig.n7 < 2000)].iloc[W::N]
print(f"worker {W}: {len(todo)} filings to repair", file=log, flush=True)
for _, r in todo.iterrows():
    d = json.load(open(r.file))
    try:
        fl = find(r.acc)
        if d.get("repair_version") != 1:
            txt = fl.text() or ""
            for k, (sp, ep) in ITEM.items():
                if len(d.get(k, "")) < 2000:
                    seg = longest_span(txt, sp, ep)
                    if len(seg) > max(2000, len(d.get(k, ""))):
                        d[k + "_regex"] = seg
            d["repair_version"] = 1
        need_ex13 = (len(d.get("item7", "")) < 2000 and len(d.get("item7_regex", "")) < 2000) or \
                    (len(d.get("item1a", "")) < 2000 and len(d.get("item1a_regex", "")) < 2000)
        if need_ex13 and not (EX13 / f"{r.acc}.txt").exists():
            ex = ""
            for a in fl.attachments:
                if (a.document_type or "").upper().startswith("EX-13"):
                    try:
                        ex += (a.text() or "") + "\n"
                    except Exception:
                        pass
            (EX13 / f"{r.acc}.txt").write_text(ex)
        json.dump(d, open(r.file, "w"))
        print(r.ticker, r.fy, "1A", len(d.get("item1a_regex", "")), "7", len(d.get("item7_regex", "")), "ex13" if need_ex13 else "", file=log, flush=True)
        time.sleep(0.3)
    except Exception as e:
        print(r.ticker, r.fy, "error", repr(e)[:150], file=log, flush=True)
        time.sleep(30 if "429" in repr(e) else 2)
print("DONE", file=log, flush=True)
