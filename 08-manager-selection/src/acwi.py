"""iShares ACWI holdings file (GICS sectors) linked to ISINs from ACWI's own Form N-PORT."""
import io
import re

import numpy as np
import pandas as pd

ISO = {"United States": "US", "Japan": "JP", "United Kingdom": "GB", "Canada": "CA", "France": "FR", "Switzerland": "CH",
       "Germany": "DE", "Taiwan": "TW", "Australia": "AU", "Netherlands": "NL", "Korea (South)": "KR", "China": "CN",
       "India": "IN", "Sweden": "SE", "Denmark": "DK", "Italy": "IT", "Spain": "ES", "Brazil": "BR", "Hong Kong": "HK",
       "Singapore": "SG", "Saudi Arabia": "SA", "South Africa": "ZA", "Finland": "FI", "Belgium": "BE", "Israel": "IL",
       "Mexico": "MX", "Indonesia": "ID", "Norway": "NO", "Thailand": "TH", "Malaysia": "MY", "Ireland": "IE",
       "United Arab Emirates": "AE", "Poland": "PL", "Qatar": "QA", "Kuwait": "KW", "Turkey": "TR", "Austria": "AT",
       "Chile": "CL", "Philippines": "PH", "Greece": "GR", "New Zealand": "NZ", "Portugal": "PT", "Hungary": "HU",
       "Peru": "PE", "Colombia": "CO", "Czech Republic": "CZ", "Egypt": "EG", "Luxembourg": "LU", "Macau": "MO",
       "Argentina": "AR", "Bermuda": "BM", "Cayman Islands": "KY", "Jersey": "JE", "Puerto Rico": "PR"}


def read_ishares(path):
    raw = open(path).read().split("\n")
    i = [k for k, l in enumerate(raw) if l.startswith("Ticker,")][0]
    d = pd.read_csv(io.StringIO("\n".join(raw[i:])))
    d = d[d["Asset Class"].notna()].copy()
    for c in ["Market Value", "Weight (%)", "Quantity", "Price"]:
        d[c] = pd.to_numeric(d[c].astype(str).str.replace(",", ""), errors="coerce")
    return d


def norm(s):
    s = str(s).upper().replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\b(INC|CORP|CORPORATION|CO|LTD|LIMITED|PLC|AG|SA|NV|SE|ASA|AB|THE|CLASS|CL|ORD|SHS|REG|HLDGS?|HOLDINGS?|GROUP|GRP)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def link(ish: pd.DataFrame, nport: pd.DataFrame) -> pd.DataFrame:
    """Attach ISIN to each iShares equity line by exact normalized-name match: first within the same country,
    then in any country (iShares 'Location' is the listing market; N-PORT 'country' is the domicile).
    Unmatched lines keep a blank ISIN rather than risk a wrong link."""
    eq = ish[ish["Asset Class"] == "Equity"].copy()
    eq["cc"] = eq["Location"].map(ISO).fillna(eq["Location"])
    eq["key"] = eq["Name"].map(norm)
    n = nport[nport["asset_cat"].isin(["EC", "EP"])].copy()
    n["key"] = n["title"].map(norm)
    n["cc"] = n["country"]
    out = eq.merge(n[["key", "cc", "isin", "pct_val"]].drop_duplicates(["key", "cc"]), on=["key", "cc"], how="left")
    used = set(out["isin"].dropna())
    # pass 2: exact name match in any country (iShares 'Location' is the market, N-PORT country is the domicile)
    for i in out.index[out["isin"].isna()]:
        c = n[(n["key"] == out.at[i, "key"]) & (~n["isin"].isin(used))]
        if len(c):
            j = (c["pct_val"] - out.at[i, "Weight (%)"]).abs().idxmin()
            out.at[i, "isin"] = c.at[j, "isin"]; used.add(c.at[j, "isin"])
    return out
