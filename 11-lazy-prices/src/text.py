"""Text cleaning, cosine similarity and Loughran-McDonald tone for 10-K sections (Project 15)."""
from __future__ import annotations

import re
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

STOP = set(ENGLISH_STOP_WORDS)


def section(rec, key):
    """Item text, falling back to the Exhibit 13 extract when the 10-K incorporates it by reference."""
    t = rec.get(key, "") or ""
    if len(t) < 2000 and len(rec.get(key + "_ex13", "") or "") > len(t):
        t = rec[key + "_ex13"]
    return t


def strip_tables(t: str) -> str:
    # drop lines that are mostly numbers/symbols (table rows)
    keep = []
    for line in t.splitlines():
        letters = sum(c.isalpha() for c in line)
        digits = sum(c.isdigit() for c in line)
        if letters == 0 or digits > letters:
            continue
        keep.append(line)
    return "\n".join(keep)


def tokens(t: str):
    t = strip_tables(t).lower()
    words = re.findall(r"[a-z]+(?:'[a-z]+)?", t)
    return [w for w in words if w not in STOP and len(w) > 1]


def cosine(c1: Counter, c2: Counter) -> float:
    if not c1 or not c2:
        return np.nan
    common = set(c1) & set(c2)
    num = sum(c1[w] * c2[w] for w in common)
    den = np.sqrt(sum(v * v for v in c1.values())) * np.sqrt(sum(v * v for v in c2.values()))
    return num / den if den else np.nan


def lm_lists(path):
    d = pd.read_csv(path)
    lists = {}
    for c in ["Negative", "Uncertainty", "Litigious", "Positive"]:
        lists[c] = set(d.loc[d[c] > 0, "Word"].str.lower())
    return lists


def lm_shares(words, lists):
    """Share of words (before stop-word removal) in each Loughran-McDonald list."""
    n = len(words)
    if n == 0:
        return {k: np.nan for k in lists}
    c = Counter(words)
    return {k: sum(v for w, v in c.items() if w in s) / n for k, s in lists.items()}


def raw_words(t: str):
    return re.findall(r"[a-z]+(?:'[a-z]+)?", strip_tables(t).lower())


def sentences(t: str, min_words=5):
    t = strip_tables(t)
    t = re.sub(r"\s+", " ", t)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", t)
    return [p.strip() for p in parts if len(p.split()) >= min_words]
