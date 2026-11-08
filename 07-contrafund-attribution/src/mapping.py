"""ISIN -> exchange ticker mapping via OpenFIGI, and Bloomberg exchange codes -> Yahoo Finance suffixes."""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

# Bloomberg composite exchange code -> Yahoo suffix (primary listings)
YAHOO_SUFFIX = {"US": "", "UN": "", "UW": "", "UQ": "", "UA": "", "UR": "", "UP": "", "UF": "", "UV": "", "LN": ".L", "GY": ".DE", "GR": ".DE", "FP": ".PA", "NA": ".AS", "JP": ".T", "JT": ".T",
                "SW": ".SW", "SE": ".SW", "CN": ".TO", "CT": ".TO", "DC": ".CO", "SS": ".ST", "HK": ".HK", "TT": ".TW",
                "KS": ".KS", "IM": ".MI", "SM": ".MC", "AU": ".AX", "AT": ".AX", "BB": ".BR", "FH": ".HE", "NO": ".OL",
                "ID": ".IR", "IN": ".NS", "IB": ".NS", "BZ": ".SA", "MM": ".MX", "SP": ".SI", "IT": ".TA", "PL": ".LS",
                "AV": ".VI", "SJ": ".JO", "TB": ".BK", "MK": ".KL", "NZ": ".NZ", "CH": ".SS", "C1": ".SS", "CG": ".SS",
                "CS": ".SZ"}
COUNTRY_EXCH = {"US": "US", "GB": "LN", "DE": "GR", "FR": "FP", "NL": "NA", "JP": "JP", "CH": "SW", "CA": "CN",
                "DK": "DC", "SE": "SS", "HK": "HK", "TW": "TT", "KR": "KS", "IT": "IM", "ES": "SM", "AU": "AU",
                "BE": "BB", "FI": "FH", "NO": "NO", "IE": "ID", "IN": "IN", "BR": "BZ", "MX": "MM", "SG": "SP",
                "IL": "IT", "PT": "PL", "AT": "AV", "ZA": "SJ", "CN": "CH", "KY": "HK", "BM": "US", "JE": "LN", "LU": "NA"}


def openfigi(isins, cache: Path, sleep=2.6):
    """Map ISINs to OpenFIGI listings (all exchanges). Cached as JSON."""
    cache = Path(cache)
    known = json.loads(cache.read_text()) if cache.exists() else {}
    todo = [i for i in dict.fromkeys(isins) if i and i not in known]
    for k in range(0, len(todo), 10):
        batch = todo[k:k + 10]
        for attempt in range(6):
            r = requests.post("https://api.openfigi.com/v3/mapping",
                              json=[{"idType": "ID_ISIN", "idValue": i, "marketSecDes": "Equity"} for i in batch], timeout=60)
            if r.status_code == 200:
                break
            time.sleep(15 * (attempt + 1))
        r.raise_for_status()
        for i, res in zip(batch, r.json()):
            known[i] = res.get("data", [])
        cache.write_text(json.dumps(known))
        time.sleep(sleep)
    return known


# Exchange to prefer for a security's ISIN country prefix when it is not USD-denominated
ISIN_EXCH = {**COUNTRY_EXCH, "CN": "HK", "KY": "HK", "BM": "HK"}
# Holdings OpenFIGI could not map, identified by name (public tickers)
MANUAL = {"US7731221062": ["RKLB"], "CA68634K1066": ["OLA.TO", "ORLA"], "US46579R2031": ["IVN.TO"],
          "US22663K1079": ["CRNX"]}


def candidates(isin, listings, currency):
    """Ordered Yahoo ticker candidates: USD securities -> US listing first; otherwise the home market."""
    if isin in MANUAL:
        return MANUAL[isin]
    out = []
    home = "US" if (currency == "USD" or isin.startswith("US")) else ISIN_EXCH.get(isin[:2], "US")
    us = ["US", "UN", "UW", "UQ", "UA", "UR", "UP", "UF", "UV"]
    order = ([home] if home != "US" else []) + us + [e for e in YAHOO_SUFFIX if e not in us + [home]]
    if home == "US":
        order = us + [e for e in YAHOO_SUFFIX if e not in us]
    for ex in order:
        for l in listings:
            if l.get("exchCode") == ex and l.get("ticker"):
                t = l["ticker"].replace("/", "-").replace(" ", "-")
                if ex == "HK":
                    t = t.zfill(4)
                y = t + YAHOO_SUFFIX[ex]
                if y not in out and "*" not in y:
                    out.append(y)
    # a delisted US security may only show foreign cross-listings; also try the bare ticker
    for l in listings:
        t = (l.get("ticker") or "").replace("/", "-").replace("*", "")
        if t and t not in out:
            out.append(t)
            break
    return out[:6]
