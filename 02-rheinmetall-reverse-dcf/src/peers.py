"""Peer EBIT margins 2021–2025 (and consensus 2026–2028) from MarketScreener 'finances' pages saved on 7 Oct 2026.
The page copies are not redistributed; the extracted figures are committed as data/consensus/peers_2026-10-07.csv."""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data" / "consensus"
PEERS = {"BAE Systems": "BA.L", "Thales": "HO.PA", "Leonardo": "LDO.MI", "Saab": "SAAB-B.ST", "Kongsberg Gruppen": "KOG.OL",
         "Rheinmetall": "RHM.DE"}
CSV = D / "peers_2026-10-07.csv"


def parse(ticker):
    t = (D / f"marketscreener_finances_{ticker}_2026-10-07.txt").read_text()
    out = {}
    for name, key in [("Net sales", "Sales"), ("EBIT", "EBIT"), ("Net Debt", "Net debt")]:
        m = re.search(rf"^{name} 1\t(.+)$", t, re.M)
        vals = [None if v.strip() in ("-", "") else float(v.replace(",", "")) for v in m.group(1).split("\t")]
        out[key] = dict(zip(range(2021, 2029), vals))
    return out


def table():
    if all((D / f"marketscreener_finances_{t}_2026-10-07.txt").exists() for t in PEERS.values()):
        rows = [{"company": n, "metric": k, "year": y, "value": v} for n, t in PEERS.items() for k, d in parse(t).items()
                for y, v in d.items() if v is not None]
        pd.DataFrame(rows).to_csv(CSV, index=False)
    return pd.read_csv(CSV)


def margins():
    T = table()
    p = T.pivot_table(index=["company", "year"], columns="metric", values="value")
    m = (p["EBIT"] / p["Sales"]).unstack("year")
    return m


if __name__ == "__main__":
    m = margins()
    print(m.round(3))
    hist = m[[2021, 2022, 2023, 2024, 2025]]
    print(pd.DataFrame({"5y avg": hist.mean(axis=1), "best 2021-25": hist.max(axis=1)}).round(3))
