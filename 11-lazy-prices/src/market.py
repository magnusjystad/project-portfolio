"""Market data for the portfolio test: monthly total returns (yfinance) and month-end market capitalisation
(shares outstanding from the SEC XBRL cover page, dei:EntityCommonStockSharesOutstanding, summed over share
classes; where that is missing, us-gaap:WeightedAverageNumberOfSharesOutstandingBasic; put on today's split basis with yfinance split history, times the split-adjusted close).

    python src/market.py
"""
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
from common import data as D  # noqa: E402

DATA = ROOT / "data"
UA = {"User-Agent": "Investment research portfolio magjys@hotmail.com"}
START, END = "2012-01-01", "2026-10-01"


def tickers():
    t = pd.read_csv(DATA / "sp100_constituents_wikipedia.csv")["Symbol"].tolist()
    return {s: s.replace(".", "-") for s in t}          # SEC/Wikipedia symbol -> Yahoo symbol


def get_prices():
    yt = list(tickers().values())
    adj = D.prices(yt, START, END, DATA / "prices_adj_daily.csv")
    raw_f = DATA / "prices_close_daily.csv"          # split-adjusted, not dividend-adjusted
    if not raw_f.exists():
        c = yf.download(yt, start=START, end=END, auto_adjust=False, progress=False, threads=False)["Close"][yt]
        c.to_csv(raw_f)
    close = pd.read_csv(raw_f, index_col=0, parse_dates=True)
    return adj, close


def get_splits():
    f = DATA / "splits.csv"
    if f.exists():
        return pd.read_csv(f, parse_dates=["date"])
    rows = []
    for t in tickers().values():
        s = yf.Ticker(t).splits
        for d, r in s.items():
            rows.append({"ticker": t, "date": pd.Timestamp(d).tz_localize(None).normalize(), "ratio": float(r)})
        time.sleep(0.3)
    out = pd.DataFrame(rows, columns=["ticker", "date", "ratio"])
    out.to_csv(f, index=False)
    return out


def get_shares():
    f = DATA / "shares_outstanding_xbrl.csv"
    if f.exists():
        return pd.read_csv(f, parse_dates=["end", "filed"])
    m = requests.get("https://www.sec.gov/files/company_tickers.json", headers=UA, timeout=60).json()
    cik = {v["ticker"].upper(): int(v["cik_str"]) for v in m.values()}
    rows = []
    for sec_t, y_t in tickers().items():
        c = cik.get(sec_t.upper()) or cik.get(sec_t.upper().replace(".", "-"))
        if c is None:
            print("no CIK", sec_t); continue
        r = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{c:010d}.json", headers=UA, timeout=60)
        time.sleep(0.15)
        if r.status_code != 200:
            print("no facts", sec_t, r.status_code); continue
        fx = r.json().get("facts", {})
        for ns, concept in [("dei", "EntityCommonStockSharesOutstanding"), ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic")]:
            for x in fx.get(ns, {}).get(concept, {}).get("units", {}).get("shares", []):
                if x.get("form") not in ("10-K", "10-Q", "10-K/A", "10-Q/A"):
                    continue
                rows.append({"ticker": y_t, "cik": c, "concept": concept, "end": x["end"], "val": float(x["val"]),
                             "form": x.get("form"), "filed": x.get("filed"), "accn": x.get("accn"), "frame": x.get("frame")})
    out = pd.DataFrame(rows)
    out.to_csv(f, index=False)
    return pd.read_csv(f, parse_dates=["end", "filed"])


def market_cap(close, splits, shares):
    """Month-end market cap in USD. Classes reported in the same filing for the same date are summed."""
    # Primary: cover-page count (classes in the same filing and date summed). Fallback where the cover count is
    # not reported without a class dimension (multi-class issuers): weighted-average basic shares, latest period
    # in each filing.
    dei = shares[shares["concept"] == "EntityCommonStockSharesOutstanding"]
    dei = dei.groupby(["ticker", "accn", "end"], as_index=False).agg(val=("val", "sum"), filed=("filed", "first"))
    dei = dei[dei["val"] > 0].sort_values(["ticker", "end", "filed"]).drop_duplicates(["ticker", "end"], keep="first")
    wa = shares[shares["concept"] == "WeightedAverageNumberOfSharesOutstandingBasic"]
    wa = wa[wa["val"] > 0].sort_values(["ticker", "accn", "end"]).groupby(["ticker", "accn"], as_index=False).last()
    wa = wa.sort_values(["ticker", "end", "filed"]).drop_duplicates(["ticker", "end"], keep="first")[["ticker", "accn", "end", "val", "filed"]]
    dei["src"], wa["src"] = "dei", "wa"
    out, src = {}, {}
    me = close.resample("ME").last()
    sp_all = splits
    for t in me.columns:
        sp = sp_all[sp_all["ticker"] == t]
        series = {}
        for name, tab in [("dei", dei), ("wa", wa)]:
            s = tab[tab["ticker"] == t]
            if s.empty:
                continue
            # put each share count on today's split basis (the basis of yfinance's split-adjusted close)
            factor = s["end"].map(lambda d: float(sp.loc[sp["date"] > d, "ratio"].prod()) if len(sp) else 1.0)
            v = pd.Series((s["val"] * factor).values, index=pd.DatetimeIndex(s["filed"].values)).sort_index()  # known when filed
            v = v[~v.index.duplicated(keep="last")]
            idx = me.index.union(v.index)
            last = pd.Series(v.index, index=v.index).reindex(idx).ffill().reindex(me.index)
            val = v.reindex(idx).ffill().reindex(me.index)
            series[name] = val.where((me.index - last).dt.days <= 400)      # stale after ~13 months
        if not series:
            continue
        sh_t = series.get("dei", pd.Series(index=me.index, dtype=float))
        used = pd.Series(sh_t.notna().map({True: "dei", False: None}), index=me.index)
        if "wa" in series:
            fill = sh_t.isna() & series["wa"].notna()
            sh_t = sh_t.fillna(series["wa"]); used[fill] = "wa"
        out[t] = me[t] * sh_t
        src[t] = used
    pd.DataFrame(src).to_csv(DATA / "market_cap_source.csv")
    return pd.DataFrame(out)


if __name__ == "__main__":
    adj, close = get_prices()
    R = D.monthly_returns(adj)
    R.to_csv(DATA / "returns_monthly.csv")
    sp, sh = get_splits(), get_shares()
    mc = market_cap(close, sp, sh)
    mc.to_csv(DATA / "market_cap_monthly.csv")
    print(R.shape, mc.shape, "missing returns:", R.columns[R.isna().all()].tolist())
    print((mc.iloc[-1] / 1e9).describe().round(1))
