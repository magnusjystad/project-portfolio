"""Trading comparables inputs: prices and share counts from yfinance (7 Oct 2026), consensus EBIT, EPS and net debt
from the MarketScreener 'finances' pages saved in data/consensus/ on 7 Oct 2026."""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PEERS = {"Rational": "RAA.DE", "Middleby": "MIDD", "Electrolux Professional": "EPRO-B.ST", "Hoshizaki": "6465.T"}
NTM_W1 = (pd.Timestamp("2026-12-31") - pd.Timestamp("2026-10-07")).days / 365     # share of FY2026 in the next 12 months


CONS_CSV = DATA / "consensus" / "consensus_2026-10-07.csv"


def consensus(ticker):
    """EBIT, EPS and net debt by fiscal year. Parsed from the saved MarketScreener page when it is present (the page copies
    are not redistributed), otherwise read from the extracted CSV committed with the project."""
    src = DATA / "consensus" / f"marketscreener_finances_{ticker}_2026-10-07.txt"
    if not src.exists():
        c = pd.read_csv(CONS_CSV)
        c = c[c["ticker"] == ticker]
        return {m: dict(zip(c.loc[c["metric"] == m, "year"], c.loc[c["metric"] == m, "value"])) for m in ["EBIT", "EPS", "Net Debt"]}
    t = src.read_text()
    def row(name):
        m = re.search(rf"^{re.escape(name)} 1\t(.+)$", t, re.M)
        vals = [v.replace(",", "") for v in m.group(1).split("\t")]
        return dict(zip(range(2021, 2029), [float(v) if v not in ("-", "") else None for v in vals]))
    return {"EBIT": row("EBIT"), "EPS": row("EPS"), "Net Debt": row("Net Debt")}


def comps_table():
    px = pd.read_csv(DATA / "market" / "prices_daily.csv", index_col=0, parse_dates=True).loc[:"2026-10-07"]
    info = json.load(open(DATA / "market" / "yfinance_info_2026-10-07.json"))
    rows = {}
    for name, tk in PEERS.items():
        c = consensus(tk)
        price = float(px[tk].dropna().iloc[-1])
        shares = 11.37e6 if tk == "RAA.DE" else float(info[tk]["impliedSharesOutstanding"])
        rows[name] = {"Price (local)": price, "Market cap (local m)": price * shares / 1e6,
                      "Net debt (local m)": c["Net Debt"][2026], "EBIT FY1": c["EBIT"][2026], "EBIT FY2": c["EBIT"][2027],
                      "EPS FY1": c["EPS"][2026], "EPS FY2": c["EPS"][2027], "NTM weight FY1": NTM_W1,
                      "Currency": info[tk]["currency"], "Price date": str(px[tk].dropna().index[-1].date())}
    T = pd.DataFrame(rows).T
    notes = ["Price: last close on or before 7 Oct 2026 (yfinance). Shares: yfinance (Electrolux Professional A + B shares; Rational 11.37m).",
             "EBIT, EPS and net debt: MarketScreener consensus pages retrieved 7 Oct 2026; FY1 = 2026, FY2 = 2027; net debt = FY2026 estimate.",
             f"NTM = {NTM_W1:.3f} × FY2026 + {1 - NTM_W1:.3f} × FY2027 (Middleby's fiscal year ends on the Saturday nearest 31 December).",
             "All multiples are in local currency, so no FX conversion is needed."]
    return T, notes


def save_consensus_csv():
    rows = []
    for tk in PEERS.values():
        for m, d in consensus(tk).items():
            rows += [{"ticker": tk, "metric": m, "year": y, "value": v} for y, v in d.items() if v is not None]
    pd.DataFrame(rows).to_csv(CONS_CSV, index=False)


if __name__ == "__main__":
    save_consensus_csv()
    T, n = comps_table()
    T["NTM EBIT"] = T["NTM weight FY1"] * T["EBIT FY1"] + (1 - T["NTM weight FY1"]) * T["EBIT FY2"]
    T["NTM EPS"] = T["NTM weight FY1"] * T["EPS FY1"] + (1 - T["NTM weight FY1"]) * T["EPS FY2"]
    T["EV/EBIT"] = (T["Market cap (local m)"] + T["Net debt (local m)"]) / T["NTM EBIT"]
    T["P/E"] = T["Price (local)"] / T["NTM EPS"]
    print(T.to_string())
