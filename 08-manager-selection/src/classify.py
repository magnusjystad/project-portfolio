"""GICS sector and listing country for fund holdings: ISIN -> OpenFIGI home-market ticker -> iShares ACWI
row with the same ticker and country (GICS). Holdings not in ACWI fall back to the yfinance sector,
mapped to the closest GICS sector name."""
import json
import re
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

from src import mapping

EXCH_CC = {"US": "US", "UN": "US", "UW": "US", "UQ": "US", "UA": "US", "UR": "US", "UP": "US", "UF": "US", "UV": "US",
           "LN": "GB", "GR": "DE", "GY": "DE", "FP": "FR", "NA": "NL", "JP": "JP", "JT": "JP", "SW": "CH", "SE": "CH",
           "CN": "CA", "CT": "CA", "DC": "DK", "SS": "SE", "HK": "HK", "TT": "TW", "KS": "KR", "IM": "IT", "SM": "ES",
           "AU": "AU", "AT": "AU", "BB": "BE", "FH": "FI", "NO": "NO", "ID": "IE", "IN": "IN", "IB": "IN", "BZ": "BR",
           "MM": "MX", "SP": "SG", "IT": "IL", "PL": "PT", "AV": "AT", "SJ": "ZA", "C1": "CN", "CH": "CN", "CS": "CN",
           "CG": "CN", "AB": "SA", "TB": "TH", "MK": "MY", "IJ": "ID", "PM": "PH", "QD": "QA", "DH": "AE", "UH": "AE",
           "TI": "TR", "PW": "PL", "CI": "CL", "GA": "GR", "NZ": "NZ"}
YAHOO_TO_GICS = {"Technology": "Information Technology", "Healthcare": "Health Care", "Financial Services": "Financials",
                 "Consumer Cyclical": "Consumer Discretionary", "Consumer Defensive": "Consumer Staples",
                 "Basic Materials": "Materials", "Communication Services": "Communication Services",
                 "Industrials": "Industrials", "Energy": "Energy", "Utilities": "Utilities", "Real Estate": "Real Estate"}


def _ex(l):
    return str(l.get("exchCode") or "").split(" ")[0]


def tknorm(t, cc=None):
    t = re.sub(r"[^A-Z0-9]", "", str(t).upper())
    return t.lstrip("0") if cc == "HK" else t


def namenorm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", str(s).upper().replace("&", " AND "))).strip()


def home_listing(isin, listings, currency):
    """(ticker, country) of the primary listing in the security's home market."""
    home = "US" if (isin.startswith("US") or currency == "USD") else mapping.ISIN_EXCH.get(isin[:2], "US")
    pref = [home] + (["UN", "UW", "UQ", "UA", "UR", "UF"] if home == "US" else [])
    for ex in pref + list(EXCH_CC):
        for l in listings:
            if _ex(l) == ex and l.get("ticker"):
                return l["ticker"].split(" ")[0].replace("/", "."), EXCH_CC[ex]
    return None, None


def classify(holdings: pd.DataFrame, ish: pd.DataFrame, figi_cache: Path, yf_cache: Path):
    figi = mapping.openfigi(holdings["isin"].dropna().unique().tolist(), figi_cache)
    ish = ish[ish["Asset Class"] == "Equity"].copy()
    from src.acwi import ISO
    ish["cc"] = ish["Location"].map(ISO).fillna(ish["Location"])
    ish["tk"] = ish["Ticker"].astype(str).str.replace(r"\.0$", "", regex=True).str.upper()
    idx = {(tknorm(t, c), c): (s, l) for t, c, s, l in zip(ish["tk"], ish["cc"], ish["Sector"], ish["Location"])}
    nidx = {(namenorm(n), c): (s, l) for n, c, s, l in zip(ish["Name"], ish["cc"], ish["Sector"], ish["Location"])}
    ycache = json.loads(Path(yf_cache).read_text()) if Path(yf_cache).exists() else {}
    rows = []
    for _, h in holdings.iterrows():
        isin = h["isin"]
        tk, cc = home_listing(isin, figi.get(isin, []), h.get("currency")) if isinstance(isin, str) else (None, None)
        hit = idx.get((tknorm(tk, cc), cc)) if tk else None
        if not hit:   # same-country exact name (punctuation-insensitive), e.g. Singapore numeric codes
            for nm in (h.get("title"), h.get("name")):
                hit = hit or nidx.get((namenorm(nm), cc or h.get("country")))
        if hit:
            rows.append({"isin": isin, "sector": hit[0], "location": hit[1], "sector_source": "iShares GICS", "ticker": tk})
            continue
        sec = None
        if isinstance(isin, str):
            if isin not in ycache:
                yt = None
                for c in mapping.candidates(isin, figi.get(isin, []), h.get("currency"))[:2]:
                    try:
                        info = yf.Ticker(c).info
                        if info.get("sector"):
                            yt = {"ticker": c, "sector": info.get("sector"), "country": info.get("country")}
                            break
                    except Exception:
                        time.sleep(5)
                ycache[isin] = yt
                Path(yf_cache).write_text(json.dumps(ycache))
                time.sleep(0.5)
            if ycache.get(isin):
                sec = YAHOO_TO_GICS.get(ycache[isin]["sector"], ycache[isin]["sector"])
        rows.append({"isin": isin, "sector": sec or "Unclassified", "location": h.get("country"),
                     "sector_source": "yfinance" if sec else "none", "ticker": tk})
    return pd.DataFrame(rows)
