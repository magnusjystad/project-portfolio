"""Daglige spotpriser (day-ahead) i prisområde NO1 fra hvakosterstrommen.no (Nord Pool-data), 2025 og 2026 hittil.
Skriver data/spotpris_NO1_daglig.csv (øre/kWh eks. mva., uvektet gjennomsnitt av timepriser/kvartersperioder).

    python src/hent_strompris.py
"""
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
URL = "https://www.hvakosterstrommen.no/api/v1/prices/{y}/{m:02d}-{d:02d}_NO1.json"

if __name__ == "__main__":
    rows, d = [], date(2025, 1, 1)
    s = requests.Session()
    while d <= date(2026, 10, 29):
        r = s.get(URL.format(y=d.year, m=d.month, d=d.day), timeout=30)
        if r.ok:
            p = [x["NOK_per_kWh"] for x in r.json()]
            rows.append({"dato": d.isoformat(), "øre/kWh": 100 * sum(p) / len(p), "perioder": len(p)})
        d += timedelta(days=1)
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "data" / "spotpris_NO1_daglig.csv", index=False)
    df["år"] = df["dato"].str[:4]
    print(df.groupby("år")["øre/kWh"].agg(["mean", "count"]).round(1))
