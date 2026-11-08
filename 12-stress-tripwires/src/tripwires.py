"""Seventeen stress tripwires: eleven market tripwires computed from data, six event tripwires checked against news.

Market tripwires use one rule. Each is calibrated on its own history up to 31 Dec 2025 (data from 2026 is out of sample):
  near = 95th percentile, fire = 99th percentile of the calibration window
  (for a downside series the 5th and 1st percentiles).
Two triggers were set by the user (MOVE 130 and JGB 30-year 4.5%). For those, "near" means within 10% of the trigger
(MOVE 117, JGB 30-year 4.05%).

  python src/tripwires.py [YYYY-MM-DD]   # as-of date (default 2026-10-07); writes data/check_<date>.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
CAL_END = "2025-12-31"
SPEED = 20                     # observations (about one month of business days) for "speed" tripwires

# id, name, column, kind, unit, source.
#   kind:  level      = value vs percentile
#          speed      = 20-observation change (difference for rates in %, % change otherwise)
#          absspeed   = absolute 20-observation % change
#          down       = weekly % change, lower tail
#          given      = level trigger set by the user
MARKET = [
    (1, "Funding: SOFR minus IORB", "SOFR - IORB (bp)", "level", "bp", "NY Fed SOFR; Fed IORB (IOER before 29 Jul 2021), via FRED"),
    (2, "Funding: Standing Repo Facility usage", "SRF usage ($bn)", "level", "$bn", "NY Fed repo operations (FRED RPONTSYD), since 28 Jul 2021"),
    (3, "Rates volatility: MOVE index", "MOVE", "given", "index", "ICE BofA MOVE index (Yahoo Finance ^MOVE)"),
    (4, "US 30-year yield, 20-day rise", "UST 30y (%)", "speed", "pp", "US Treasury constant-maturity 30y (FRED DGS30)"),
    (5, "High-yield spread, 20-day widening", "HY OAS (%)", "speed", "pp", "ICE BofA US High Yield OAS (FRED BAMLH0A0HYM2; 3 years only)"),
    (6, "Leveraged funds' Treasury futures shorts, weekly change", "CFTC lev. shorts ($bn)", "down", "%", "CFTC Traders in Financial Futures, six CBOT Treasury contracts"),
    (7, "Fed central-bank swap lines outstanding", "Fed swap lines ($m, weekly)", "level", "$m", "Federal Reserve H.4.1 (FRED SWPT)"),
    (8, "USD/JPY, 20-day move either way", "USD/JPY", "absspeed", "%", "Fed H.10 noon buying rate (FRED DEXJPUS)"),
    (9, "JGB 30-year yield", "JGB 30y (%)", "given", "%", "Ministry of Finance Japan benchmark yields"),
    (10, "Brent crude futures, 20-day rise", "Brent futures ($)", "speed", "%", "ICE Brent front-month futures (Yahoo Finance BZ=F)"),
    (11, "Equity volatility: VIX", "VIX", "level", "index", "Cboe VIX (FRED VIXCLS)"),
]
GIVEN = {"MOVE": 130.0, "JGB 30y (%)": 4.5}


def load():
    I = pd.read_csv(D / "indicators_daily.csv", index_col=0, parse_dates=True)
    W = pd.read_csv(D / "cftc_leveraged_shorts_weekly.csv", index_col=0, parse_dates=True)
    cols = [c for c in W.columns if c != "Total"]
    prev = W[cols].shift(1)
    both = W[cols].notna() & prev.notna()          # contracts present in both weeks (Ultra 10-year only from 2016)
    W["chg_pct"] = (W[cols].where(both).sum(axis=1) / prev.where(both).sum(axis=1) - 1) * 100
    return I, W


def signal(I, W, col, kind):
    """The series the tripwire is tested on (in its own units)."""
    if kind == "down":
        return W["chg_pct"].dropna()
    s = I[col].dropna()
    if kind in ("level", "given"):
        return s
    if col.endswith("(%)"):                        # yields and spreads: change in percentage points
        return (s - s.shift(SPEED)).dropna()
    ch = (s / s.shift(SPEED) - 1) * 100
    return (ch.abs() if kind == "absspeed" else ch).dropna()


def calibrate(I, W):
    rows = []
    for tid, name, col, kind, unit, src in MARKET:
        x = signal(I, W, col, kind).loc[:CAL_END]
        if kind == "down":
            near, fire = x.quantile(0.05), x.quantile(0.01)
        elif kind == "given":
            fire = GIVEN[col]
            near = 0.9 * fire
        else:
            near, fire = x.quantile(0.95), x.quantile(0.99)
        share = lambda t: float((x <= t).mean() if kind == "down" else (x >= t).mean())
        rows.append({"id": tid, "tripwire": name, "series": col, "kind": kind, "unit": unit, "near": near, "fire": fire,
                     "share of days at or beyond near": share(near), "share of days at or beyond fire": share(fire),
                     "calibration": f"{x.index[0].date()} – {x.index[-1].date()}", "observations": len(x), "source": src})
    return pd.DataFrame(rows).set_index("id")


def status(v, near, fire, kind):
    if pd.isna(v):
        return "no data"
    if kind == "down":
        return "FIRED" if v <= fire else ("near" if v <= near else "ok")
    return "FIRED" if v >= fire else ("near" if v >= near else "ok")


def market_check(asof, I=None, W=None, T=None):
    """Latest value on or before the day before `asof` (the last complete session), and the value one week earlier."""
    if I is None:
        I, W = load()
    T = calibrate(I, W) if T is None else T
    cut = pd.Timestamp(asof) - pd.Timedelta(days=1)
    rows = []
    for tid, r in T.iterrows():
        x = signal(I, W, r["series"], r["kind"]).loc[:cut]
        raw = (W["Total"] if r["kind"] == "down" else I[r["series"]]).dropna().loc[:cut]
        wk = raw.loc[:raw.index[-1] - pd.Timedelta(days=7)]
        rows.append({"id": tid, "tripwire": r["tripwire"], "date": x.index[-1].date(), "level": raw.iloc[-1],
                     "level a week earlier": wk.iloc[-1] if len(wk) else np.nan, "tested value": x.iloc[-1],
                     "near": r["near"], "fire": r["fire"], "status": status(x.iloc[-1], r["near"], r["fire"], r["kind"])})
    return pd.DataFrame(rows).set_index("id")


def history(I, W, T, start="2007-01-01"):
    """Daily status of each market tripwire (2 = fired, 1 = near, 0 = ok, NaN = no data) on business days."""
    idx = pd.bdate_range(start, I.index.max())
    out = {}
    for tid, r in T.iterrows():
        x = signal(I, W, r["series"], r["kind"])
        x = x.reindex(idx, method="ffill", limit=7 if r["kind"] == "down" or "weekly" in r["series"] else 3)
        if r["kind"] == "down":
            st = np.where(x <= r["fire"], 2, np.where(x <= r["near"], 1, 0))
        else:
            st = np.where(x >= r["fire"], 2, np.where(x >= r["near"], 1, 0))
        out[tid] = pd.Series(st, index=idx).where(x.notna())
    return pd.DataFrame(out)


if __name__ == "__main__":
    asof = sys.argv[1] if len(sys.argv) > 1 else "2026-10-07"
    I, W = load()
    T = calibrate(I, W)
    T.to_csv(D / "thresholds.csv")
    C = market_check(asof, I, W, T)
    C.to_csv(D / f"check_{asof}.csv")
    pd.set_option("display.width", 220)
    print(T[["tripwire", "kind", "near", "fire", "calibration", "observations"]].round(2).to_string())
    print(C.round(3).to_string())
