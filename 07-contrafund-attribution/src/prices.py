"""Quarter-end total-return prices (USD) for N-PORT holdings, from yfinance."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from src import mapping

QDATES = ["2024-12-31", "2025-03-31", "2025-06-30", "2025-09-30", "2025-12-31"]
SUFFIX_CCY = {".L": "GBP", ".DE": "EUR", ".PA": "EUR", ".AS": "EUR", ".T": "JPY", ".SW": "CHF", ".TO": "CAD",
              ".CO": "DKK", ".ST": "SEK", ".HK": "HKD", ".TW": "TWD", ".KS": "KRW", ".MI": "EUR", ".MC": "EUR",
              ".AX": "AUD", ".BR": "EUR", ".HE": "EUR", ".OL": "NOK", ".IR": "EUR", ".NS": "INR", ".SA": "BRL",
              ".MX": "MXN", ".SI": "SGD", ".TA": "ILS", ".LS": "EUR", ".VI": "EUR", ".JO": "ZAR", ".BK": "THB",
              ".KL": "MYR", ".NZ": "NZD", ".SS": "CNY", ".SZ": "CNY"}


def ccy_of(ticker):
    for s, c in SUFFIX_CCY.items():
        if ticker.endswith(s):
            return c
    return "USD"


def download(tickers, start="2024-12-15", end="2026-01-10", batch=40):
    """Batched, retried yfinance download (Yahoo rate-limits large requests)."""
    import time
    tickers = list(tickers)
    frames = []
    for k in range(0, len(tickers), batch):
        part = tickers[k:k + batch]
        got = None
        for attempt in range(5):
            df = yf.download(part, start=start, end=end, auto_adjust=True, progress=False, threads=False)["Close"]
            if isinstance(df, pd.Series):
                df = df.to_frame(part[0])
            got = df
            ok = df.notna().any().sum()
            if ok >= max(1, int(0.6 * len(part))) or attempt == 4:
                break
            time.sleep(20 * (attempt + 1))
        frames.append(got)
        time.sleep(2)
    return pd.concat(frames, axis=1)


def quarter_end(px: pd.DataFrame, dates=QDATES):
    """Last available close on or before each date (stale by at most 5 business days)."""
    out = {}
    for d in dates:
        sub = px.loc[:d]
        last = sub.ffill(limit=5).iloc[-1] if len(sub) else pd.Series(np.nan, px.columns)
        out[d] = last
    return pd.DataFrame(out).T


def build(sec: pd.DataFrame, figi: dict, cache: Path):
    """Pick the first candidate ticker per ISIN with prices at all quarter ends it needs; USD prices."""
    cache = Path(cache)
    chosen, px_all = {}, {}
    if cache.exists():                     # resume: keep what is already priced, retry the rest
        old = pd.read_csv(cache, index_col=0)
        chosen = json.load(open(cache.with_suffix(".json")))
        sec = sec.loc[[i for i in sec.index if i not in chosen]]
    else:
        old = None
    cands = {i: mapping.candidates(i, figi.get(i, []), r["currency"]) for i, r in sec.iterrows()}
    done_before = dict(chosen)
    for round_ in range(6):
        need = {i: c[round_] for i, c in cands.items() if i not in chosen and len(c) > round_}
        if not need:
            break
        px = quarter_end(download(sorted(set(need.values()))))
        for i, t in need.items():
            if t in px.columns and px[t].notna().sum() >= 2:
                chosen[i] = t
                px_all[t] = px[t]
    P = pd.DataFrame(px_all) if px_all else pd.DataFrame(index=QDATES)
    fx_ccy = sorted({ccy_of(t) for t in P.columns} - {"USD"})
    fx = quarter_end(download([f"{c}USD=X" for c in fx_ccy])) if fx_ccy else pd.DataFrame(index=P.index)
    usd = P.copy()
    for t in P.columns:
        c = ccy_of(t)
        if c != "USD":
            usd[t] = P[t] * fx[f"{c}USD=X"]
    out = pd.DataFrame({i: usd[t] for i, t in chosen.items() if i not in done_before and t in usd.columns})
    if old is not None:
        out = pd.concat([old, out], axis=1)
    out.to_csv(cache)
    json.dump(chosen, open(cache.with_suffix(".json"), "w"), indent=1)
    return out, chosen
