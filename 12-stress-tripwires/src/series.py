"""Builds the indicator series for the market tripwires from the raw files in data/raw/ (see src/fetch.py).

    python src/series.py      # writes data/indicators_daily.csv and data/cftc_leveraged_shorts_weekly.csv
"""
import io
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

# CFTC Traders in Financial Futures: Treasury futures and their face value per contract (CBOT contract specs)
UST_FUTURES = {"042601": ("2-year note", 200_000), "044601": ("5-year note", 100_000), "043602": ("10-year note", 100_000),
               "043607": ("Ultra 10-year", 100_000), "020601": ("Bond", 100_000), "020604": ("Ultra bond", 100_000)}


def fred(sid):
    s = pd.read_csv(RAW / f"fred_{sid}.csv", index_col=0, parse_dates=True, na_values=".").iloc[:, 0]
    return pd.to_numeric(s, errors="coerce").dropna().rename(sid)


def yahoo(name):
    s = pd.read_csv(RAW / f"yahoo_{name}.csv", index_col=0, parse_dates=True)["Close"]
    return pd.to_numeric(s, errors="coerce").dropna().rename(name)


def jgb30():
    """MoF Japan benchmark yields: historical file plus the current-month file; 30-year column."""
    out = []
    for f in ["mof_jgb_historical.csv", "mof_jgb_current_month.csv"]:
        d = pd.read_csv(RAW / f, skiprows=1, encoding="latin-1")
        d = d[pd.to_datetime(d["Date"], format="%Y/%m/%d", errors="coerce").notna()]
        out.append(pd.Series(pd.to_numeric(d["30Y"], errors="coerce").values,
                             index=pd.to_datetime(d["Date"], format="%Y/%m/%d")))
    s = pd.concat(out).dropna()
    return s[~s.index.duplicated(keep="last")].sort_index().rename("JGB30")


def cftc_leveraged_shorts():
    """Leveraged funds' short positions in the six Treasury futures, in $bn of face value, weekly (Tuesday)."""
    rows = []
    for z in sorted(RAW.glob("cftc_fin_*.zip")):
        zf = zipfile.ZipFile(z)
        d = pd.read_csv(io.BytesIO(zf.read(zf.namelist()[0])), low_memory=False, dtype={"CFTC_Contract_Market_Code": str})
        d["code"] = d["CFTC_Contract_Market_Code"].str.strip().str.zfill(6)
        d = d[d["code"].isin(UST_FUTURES)]
        dcol = "Report_Date_as_YYYY-MM-DD" if "Report_Date_as_YYYY-MM-DD" in d else "Report_Date_as_MM_DD_YYYY"
        for _, r in d.iterrows():
            rows.append({"date": pd.Timestamp(r[dcol]), "contract": UST_FUTURES[r["code"]][0],
                         "short_bn": float(r["Lev_Money_Positions_Short_All"]) * UST_FUTURES[r["code"]][1] / 1e9})
    w = pd.DataFrame(rows).drop_duplicates(["date", "contract"]).pivot(index="date", columns="contract", values="short_bn").sort_index()
    w["Total"] = w.sum(axis=1, min_count=1)
    return w


def build():
    sofr, iorb, ioer = fred("SOFR"), fred("IORB"), fred("IOER")
    admin = pd.concat([ioer[ioer.index < "2021-07-29"], iorb]).sort_index()            # IORB replaced IOER on 29 Jul 2021
    admin = admin.reindex(sofr.index, method="ffill")
    ind = pd.DataFrame({
        "SOFR": sofr, "IORB/IOER": admin, "SOFR - IORB (bp)": (sofr - admin) * 100,
        "SRF usage ($bn)": fred("RPONTSYD").loc["2021-07-28":],                          # Standing Repo Facility from 28 Jul 2021
        "MOVE": yahoo("MOVE"), "VIX": fred("VIXCLS"),
        "UST 10y (%)": fred("DGS10"), "UST 30y (%)": fred("DGS30"),
        "HY OAS (%)": fred("BAMLH0A0HYM2"), "USD/JPY": fred("DEXJPUS"),
        "JGB 30y (%)": jgb30(), "Brent futures ($)": yahoo("BZ_F"), "Brent spot ($)": fred("DCOILBRENTEU"),
        "Fed swap lines ($m, weekly)": fred("SWPT"),
    })
    ind.index.name = "date"
    return ind


if __name__ == "__main__":
    ind = build()
    ind.to_csv(ROOT / "data" / "indicators_daily.csv")
    w = cftc_leveraged_shorts()
    w.to_csv(ROOT / "data" / "cftc_leveraged_shorts_weekly.csv")
    print(ind.loc["2026-09-24":].round(3).to_string())
    print(w.tail(4).round(1).to_string())
