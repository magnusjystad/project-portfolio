"""Download and parse Form N-PORT-P holdings from SEC EDGAR."""
from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import requests

UA = {"User-Agent": "Investment research portfolio magjys@hotmail.com"}
NS = {"n": "http://www.sec.gov/edgar/nport"}


def _get(url):
    for i in range(5):
        r = requests.get(url, headers=UA, timeout=120)
        if r.status_code == 200:
            time.sleep(0.15)
            return r
        time.sleep(2 ** i)
    r.raise_for_status()


def list_filings(cik: str) -> pd.DataFrame:
    j = _get(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json").json()
    frames = [pd.DataFrame(j["filings"]["recent"])]
    for f in j["filings"].get("files", []):
        frames.append(pd.DataFrame(_get("https://data.sec.gov/submissions/" + f["name"]).json()))
    d = pd.concat(frames)
    return d[d["form"] == "NPORT-P"].reset_index(drop=True)


def xml_url(cik, accession):
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/primary_doc.xml"


def header(xml_text):
    root = ET.fromstring(xml_text)
    g = lambda p: (root.find(p, NS).text if root.find(p, NS) is not None else None)
    return {"series_name": g(".//n:genInfo/n:seriesName"), "series_id": g(".//n:genInfo/n:seriesId"),
            "rep_pd_date": g(".//n:genInfo/n:repPdDate"), "total_assets": g(".//n:fundInfo/n:totAssets"),
            "net_assets": g(".//n:fundInfo/n:netAssets")}


def holdings(xml_text) -> pd.DataFrame:
    root = ET.fromstring(xml_text)
    rows = []
    for s in root.findall(".//n:invstOrSecs/n:invstOrSec", NS):
        g = lambda p: (s.find(p, NS).text if s.find(p, NS) is not None else None)
        ids = s.find("n:identifiers", NS)
        isin = ticker = other = None
        if ids is not None:
            e = ids.find("n:isin", NS)
            isin = e.get("value") if e is not None else None
            e = ids.find("n:ticker", NS)
            ticker = e.get("value") if e is not None else None
            e = ids.find("n:other", NS)
            other = e.get("value") if e is not None else None
        cc = s.find("n:currencyConditional", NS)
        cur = g("n:curCd") or (cc.get("curCd") if cc is not None else None)
        fx = cc.get("exchangeRt") if cc is not None else None
        rows.append({"name": g("n:name"), "title": g("n:title"), "lei": g("n:lei"), "cusip": g("n:cusip"),
                     "isin": isin, "ticker": ticker, "other_id": other, "balance": g("n:balance"),
                     "units": g("n:units"), "currency": cur, "fx_rate": fx, "value_usd": g("n:valUSD"),
                     "pct_val": g("n:pctVal"), "asset_cat": g("n:assetCat"), "issuer_cat": g("n:issuerCat"),
                     "country": g("n:invCountry"), "fair_value_level": g("n:fairValLevel"),
                     "restricted": g("n:isRestrictedSec")})
    d = pd.DataFrame(rows)
    for c in ["balance", "value_usd", "pct_val"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d


def fetch_series(cik, series_match: str, report_dates, cache_dir: Path):
    """Holdings for the series whose name contains `series_match` at each report date (YYYY-MM-DD)."""
    cache_dir = Path(cache_dir); cache_dir.mkdir(parents=True, exist_ok=True)
    fl = list_filings(cik)
    out, meta = {}, {}
    for d in report_dates:
        f = cache_dir / f"{series_match.replace(' ', '_')}_{d}.csv"
        if f.exists():
            out[d] = pd.read_csv(f)
            continue
        cands = fl[fl["reportDate"] == d]
        found = False
        for acc in cands["accessionNumber"]:
            x = _get(xml_url(cik, acc)).text
            h = header(x)
            if h["series_name"] and series_match.lower() == h["series_name"].strip().lower():
                hd = holdings(x)
                hd.attrs = h
                hd.to_csv(f, index=False)
                meta[d] = {**h, "accession": acc}
                out[d] = hd
                found = True
                break
        if not found:
            raise LookupError(f"{series_match} N-PORT for {d} not found among {len(cands)} filings")
    return out, meta


def series_accessions(series_id: str, count=60):
    import re
    x = _get(f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={series_id}&type=NPORT-P"
             f"&dateb=&owner=include&count={count}&output=atom").text
    return re.findall(r"<accession-number>([^<]+)</accession-number>", x)


def fetch_by_series(cik, series_id: str, report_dates, cache_dir: Path, label: str):
    """Holdings for one series at each report date, located through the series' own filing list."""
    cache_dir = Path(cache_dir); cache_dir.mkdir(parents=True, exist_ok=True)
    out, meta, todo = {}, {}, []
    for d in report_dates:
        f = cache_dir / f"{label}_{d}.csv"
        if f.exists():
            out[d] = pd.read_csv(f)
        else:
            todo.append(d)
    if not todo:
        return out, meta
    for acc in series_accessions(series_id):
        x = _get(xml_url(cik, acc)).text
        h = header(x)
        if h["series_id"] != series_id or h["rep_pd_date"] not in todo:
            continue
        hd = holdings(x)
        hd.to_csv(cache_dir / f"{label}_{h['rep_pd_date']}.csv", index=False)
        out[h["rep_pd_date"]] = hd
        meta[h["rep_pd_date"]] = {**h, "accession": acc}
        todo.remove(h["rep_pd_date"])
        if not todo:
            break
    if todo:
        raise LookupError(f"{label}: no N-PORT for {todo}")
    return out, meta
