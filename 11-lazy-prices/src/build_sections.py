"""Choose the text of Item 1A and Item 7 for each original 10-K and compute text features.
Priority per section: edgartools item (>= 5,000 chars for 1A, 8,000 for 7) > regex item from the full 10-K text > Exhibit 13 extract."""
import glob
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import text as T  # noqa: E402

RAW = ROOT / "data" / "raw_10k"
MIN = {"item1a": 5000, "item7": 8000}   # shorter extracts are cross-references or headings, not the section
MDA = re.compile(r"management[’'`]?s\s+discussion\s+and\s+analysis", re.I)
RF = re.compile(r"(?<![a-z])risk\s+factors(?![a-z])", re.I)
MDA_END = re.compile(r"report\s+of\s+independent\s+registered|management[’'`]?s\s+report\s+on\s+internal\s+control|"
                     r"statement\s+of\s+management\s+responsibility|consolidated\s+statements?\s+of\s+(income|operations|earnings|"
                     r"financial\s+position|comprehensive)|selected\s+financial\s+data|five[- ]year\s+(summary|financial)|"
                     r"quarterly\s+(financial\s+)?(information|data)|stock\s+performance\s+graph", re.I)
RF_END = re.compile(r"management[’'`]?s\s+discussion|quantitative\s+and\s+qualitative|controls\s+and\s+procedures|"
                    r"unresolved\s+staff|legal\s+proceedings|glossary|financial\s+statements", re.I)
TOC = re.compile(r"report\s+of\s+independent|consolidated\s+(balance|statements?)|selected\s+financial|notes\s+to\s+"
                 r"consolidated|\.{4,}|\bpage\b", re.I)


def from_exhibit(text, start_re, end_re, min_len, cap):
    for m in start_re.finditer(text):
        if TOC.search(text, m.end(), m.end() + 400):
            continue
        e = end_re.search(text, m.end() + min_len)
        seg = text[m.start(): e.start() if e else m.start() + cap]
        if len(seg) >= min_len:
            return seg[:cap], ("exhibit 13" if e else "exhibit 13 (capped)")
    return "", None


def pick(rec, key, ex13):
    if len(rec.get(key, "") or "") >= MIN[key]:
        return rec[key], "10-K item"
    if len(rec.get(key + "_regex", "") or "") >= MIN[key]:
        return rec[key + "_regex"], "10-K regex"
    if ex13:
        if key == "item7":
            seg, src = from_exhibit(ex13, MDA, MDA_END, 10_000, 250_000)
        else:
            seg, src = from_exhibit(ex13, RF, RF_END, 5_000, 120_000)
        if seg:
            return seg, src
    return "", "missing"


def main():
    lm = T.lm_lists(ROOT / "data" / "external" / "LM_MasterDictionary_1993-2025.csv")
    recs = []
    for f in glob.glob(str(RAW / "*_*_*.json")):
        d = json.load(open(f))
        recs.append((f, d["ticker"], int(d["period"][:4]), d["period"], d["filing_date"], d["accession"]))
    df = pd.DataFrame(recs, columns=["file", "ticker", "fy", "period", "filed", "acc"]).sort_values(["ticker", "fy", "filed"])
    orig = df.groupby(["ticker", "fy"]).first().reset_index()     # original 10-K = earliest filing for the fiscal year
    rows, counters, sents = [], {}, {}
    for _, r in orig.iterrows():
        d = json.load(open(r.file))
        exf = RAW / "ex13" / f"{r.acc}.txt"
        ex13 = exf.read_text() if exf.exists() else ""
        t1a, s1a = pick(d, "item1a", ex13)
        t7, s7 = pick(d, "item7", ex13)
        c1a, c7 = Counter(T.tokens(t1a)), Counter(T.tokens(t7))
        counters[(r.ticker, r.fy)] = (c1a, c7)
        words = T.raw_words(t1a + "\n" + t7)
        sh = T.lm_shares(words, lm)
        sents[f"{r.ticker}|{r.fy}"] = T.sentences(t7)
        rows.append({"ticker": r.ticker, "fy": r.fy, "period": r.period, "filed": r.filed, "accession": r.acc,
                     "src_1a": s1a, "src_7": s7, "len_1a": len(t1a), "len_7": len(t7), "n_words": len(words),
                     "lm_negative": sh["Negative"], "lm_uncertainty": sh["Uncertainty"], "lm_litigious": sh["Litigious"],
                     "lm_positive": sh["Positive"], "n_sent_mda": len(sents[f"{r.ticker}|{r.fy}"])})
    F = pd.DataFrame(rows).sort_values(["ticker", "fy"])
    sims = []
    for _, r in F.iterrows():
        prev = counters.get((r.ticker, r.fy - 1))
        cur = counters[(r.ticker, r.fy)]
        if prev is None:
            sims.append((np.nan, np.nan, np.nan))
            continue
        s1 = T.cosine(cur[0], prev[0]) if cur[0] and prev[0] else np.nan
        s7 = T.cosine(cur[1], prev[1]) if cur[1] and prev[1] else np.nan
        sc = T.cosine(cur[0] + cur[1], prev[0] + prev[1]) if (cur[0] or cur[1]) and (prev[0] or prev[1]) else np.nan
        sims.append((s1, s7, sc))
    F[["sim_1a", "sim_7", "sim_combined"]] = pd.DataFrame(sims, index=F.index)
    # Flag pairs whose text came from different extraction routes (item vs regex vs exhibit 13)
    g = F.groupby("ticker")
    F["src_change"] = ((F["src_1a"] != g["src_1a"].shift()) | (F["src_7"] != g["src_7"].shift())) & (g["fy"].diff() == 1)
    for c in ["lm_negative", "lm_uncertainty", "lm_litigious"]:
        F["d_" + c] = F.groupby("ticker")[c].diff().where(F.groupby("ticker")["fy"].diff() == 1)
    F.to_csv(ROOT / "data" / "text_features.csv", index=False)
    json.dump(sents, open(ROOT / "data" / "raw_10k" / "mda_sentences.json", "w"))
    print(F[["src_1a", "src_7"]].apply(pd.Series.value_counts).fillna(0).astype(int))
    print(F[["sim_1a", "sim_7", "sim_combined", "lm_negative", "n_sent_mda"]].describe().round(3))


if __name__ == "__main__":
    main()
