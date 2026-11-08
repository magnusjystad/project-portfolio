"""Rational AG valuation model (Python reference implementation; the Excel workbook reproduces it with formulas).

Reported data: annual reports 2016–2025 and the H1 2026 report (data/extract_*.csv, data/h1_2026.csv).
Market data: data/market/ (src/inputs.py). Forecast assumptions: ASSUMPTIONS below — these are the analyst's
judgements, not reported data, and each is justified in the report.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PUB = pd.Timestamp("2026-10-07")
SHARES = 11.370                    # million shares outstanding (AR 2025, H1 2026)
YEARS = list(range(2026, 2036))     # 10-year explicit forecast
HIST = list(range(2016, 2026))
REGIONS = ["Germany", "Europe ex-Germany", "North America", "Asia", "Rest of world"]
G_TERM = 0.02
WEIGHTS = {"Bear": 0.25, "Base": 0.50, "Bull": 0.25}

# ---------------------------------------------------------------------------------------------------------------------
# Analyst assumptions (see report section 6). Growth = nominal EUR sales growth by customer region.
BASE_GROWTH = {   # 2026, then 2027–2030 (flat); 2031–2035 fade linearly to FADE_TO
    "Germany": (0.07, 0.045), "Europe ex-Germany": (0.08, 0.065), "North America": (0.04, 0.08),
    "Asia": (-0.02, 0.04), "Rest of world": (0.08, 0.08)}
FADE_TO = 0.03
ASSUMPTIONS = {
    "Base": {"growth_shift_2026": 0.0, "growth_shift": 0.0, "margin": {2026: 0.255, 2027: 0.260, "later": 0.265},
             "ivario_step": (0.005, 0.003)},
    "Bear": {"growth_shift_2026": -0.02, "growth_shift": -0.03, "margin": {2026: 0.250, 2027: 0.240, "later": 0.240},
             "ivario_step": (0.002, 0.001)},
    "Bull": {"growth_shift_2026": 0.01, "growth_shift": 0.02, "margin": {2026: 0.260, 2027: 0.270, "later": 0.280},
             "ivario_step": (0.007, 0.004)},
}
COMMON = {"tax": 0.25, "da": 0.030, "capex": {2026: 0.035, 2027: 0.035, "later": 0.032}, "nwc": 0.225,
          "lease": 0.009, "payout": 0.70}


# ---------------------------------------------------------------------------------------------------------------------
def history():
    d = pd.read_csv(DATA / "extract_raw.csv", index_col=0) / 1000          # EUR m
    d.columns = d.columns.astype(int)
    return d


def regions_history():
    r = pd.read_csv(DATA / "extract_regions.csv", index_col=0)
    r.index = r.index.astype(int)
    out = pd.DataFrame({"Germany": r["Germany"], "Europe ex-Germany": r["Europe ex-Germany"], "North America": r["North America"],
                        "Asia": r["Asia"], "Rest of world": r["Latin America"] + r["Rest of world"]}) / 1000
    assert np.allclose(out.sum(axis=1), r["Sales (IS)"] / 1000)
    return out


def products_history():
    p = pd.read_csv(DATA / "extract_product_groups.csv", index_col=0)
    p.index = p.index.astype(int)
    return pd.DataFrame({"iVario": p["iVario"] / 1000, "iCombi": p["iCombi (= total - iVario)"] / 1000})


def h1_2026():
    v = pd.read_csv(DATA / "h1_2026.csv", index_col=0)["value"]
    return pd.to_numeric(v, errors="coerce").dropna()


# ---------------------------------------------------------------------------------------------------------------------
def growth_path(scn):
    a = ASSUMPTIONS[scn]
    g = {}
    for r, (g26, g27) in BASE_GROWTH.items():
        row = {2026: g26 + a["growth_shift_2026"]}
        mid = g27 + a["growth_shift"]
        for y in range(2027, 2031):
            row[y] = mid
        for i, y in enumerate(range(2031, 2036), 1):          # linear fade from the 2030 rate to FADE_TO in 2035
            row[y] = mid + (FADE_TO - mid) * i / 5
        g[r] = row
    return pd.DataFrame(g).T[YEARS]


def ivario_share_path(scn, start):
    s1, s2 = ASSUMPTIONS[scn]["ivario_step"]
    out, s = {}, start
    for y in YEARS:
        s += s1 if y <= 2030 else s2
        out[y] = s
    return pd.Series(out)


def margin_path(scn):
    m = ASSUMPTIONS[scn]["margin"]
    return pd.Series({y: m.get(y, m["later"]) for y in YEARS})


def forecast(scn):
    H, RH, PH = history(), regions_history(), products_history()
    G = growth_path(scn)
    reg = {}
    prev = RH.loc[2025]
    for y in YEARS:
        prev = prev * (1 + G[y])
        reg[y] = prev
    REG = pd.DataFrame(reg)                                  # regions x years
    share0 = PH.loc[2025, "iVario"] / H.loc["Sales revenues", 2025]
    ivs = ivario_share_path(scn, share0)
    IV = REG * ivs                                            # iVario by region (same share in every region: assumption)
    IC = REG - IV
    sales = REG.sum()
    m = margin_path(scn)
    f = pd.DataFrame(index=YEARS)
    f["Sales"] = sales
    f["Growth"] = sales.pct_change().fillna(sales[2026] / H.loc["Sales revenues", 2025] - 1)
    f["iVario"] = IV.sum(); f["iCombi"] = IC.sum(); f["iVario share"] = ivs
    f["EBIT margin"] = m; f["EBIT"] = sales * m
    f["Taxes on EBIT"] = -f["EBIT"] * COMMON["tax"]; f["NOPAT"] = f["EBIT"] + f["Taxes on EBIT"]
    f["D&A"] = sales * COMMON["da"]
    f["Capex"] = -sales * pd.Series({y: COMMON["capex"].get(y, COMMON["capex"]["later"]) for y in YEARS})
    nwc = sales * COMMON["nwc"]
    nwc_2025 = H.loc["Sales revenues", 2025] * COMMON["nwc"]
    f["Change in NWC"] = -(nwc - nwc.shift(1).fillna(nwc_2025))
    f["Lease payments"] = -sales * COMMON["lease"]
    f["FCFF"] = f["NOPAT"] + f["D&A"] + f["Capex"] + f["Change in NWC"] + f["Lease payments"]
    return f, REG, IV, IC, G


# ---------------------------------------------------------------------------------------------------------------------
def market_inputs():
    b = pd.read_csv(DATA / "market" / "bund10y_bundesbank_daily.csv", skiprows=0, encoding="utf-8-sig", header=None)
    rows = [r for r in b.itertuples(index=False) if str(r[0])[:4].isdigit()]
    bund = pd.Series({pd.Timestamp(r[0]): pd.to_numeric(r[1], errors="coerce") for r in rows}).dropna() / 100
    rf = float(bund.loc[:PUB].iloc[-1]); rf_date = bund.loc[:PUB].index[-1]
    erp_t = pd.read_excel(DATA / "market" / "damodaran_ERPbymonth.xlsx", header=0)
    erp_t = erp_t.rename(columns={erp_t.columns[0]: "month"}).dropna(subset=["month"])
    erp_t["month"] = pd.to_datetime(erp_t["month"], errors="coerce")
    erp_row = erp_t[erp_t["month"] <= PUB].iloc[-1]
    erp = float(erp_row["ERP (T12 m with sustainable payout)"])
    p = pd.read_csv(DATA / "market" / "prices_adj_daily.csv", index_col=0, parse_dates=True)
    m = p[["RAA.DE", "^STOXX"]].resample("ME").last().pct_change().loc["2021-10":"2026-09"].dropna()
    reg = sm.OLS(m["RAA.DE"], sm.add_constant(m["^STOXX"])).fit()
    raw = float(reg.params["^STOXX"])
    blume = 0.67 * raw + 0.33
    close = pd.read_csv(DATA / "market" / "prices_daily.csv", index_col=0, parse_dates=True)
    price = float(close.loc[:PUB, "RAA.DE"].dropna().iloc[-1])
    return {"rf": rf, "rf_date": str(rf_date.date()), "erp": erp, "erp_month": str(erp_row["month"].date()),
            "beta_raw": raw, "beta_se": float(reg.bse["^STOXX"]), "beta_r2": float(reg.rsquared), "beta_months": len(m),
            "beta_blume": blume, "ke": rf + blume * erp, "price": price,
            "price_date": str(close.loc[:PUB, "RAA.DE"].dropna().index[-1].date())}


def net_cash():
    h = h1_2026()
    items = {"Cash and cash equivalents": h["cash"], "Other current financial assets at amortised cost (fixed-term deposits)": h["deposits"],
             "Fund units": h["fund_units"], "Pension obligations": -h["pensions"]}
    return items, sum(items.values())


def year_fraction(d):
    return (pd.Timestamp(d) - PUB).days / 365.25


def dcf(f, ke, g=G_TERM, ncash=None):
    """EV at the publication date. FCFF of H2 2026 (half of the 2026 model year, mid-point 1 Oct 2026) and full
    years 2027–2035 (mid-year), Gordon terminal value at 31 Dec 2035. Net cash is as at 30 June 2026."""
    if ncash is None:
        ncash = net_cash()[1]
    cf = f["FCFF"].copy()
    cf[2026] = cf[2026] * 0.5
    t = pd.Series({y: year_fraction("2026-10-01" if y == 2026 else f"{y}-07-01") for y in YEARS})
    disc = (1 + ke) ** (-t)
    pv = cf * disc
    tv = f["FCFF"][2035] * (1 + g) / (ke - g)
    t_end = year_fraction("2035-12-31")
    pv_tv = tv / (1 + ke) ** t_end
    ev = pv.sum() + pv_tv
    eq = ev + ncash
    per_share = eq / SHARES
    eps26 = f["NOPAT"][2026] / SHARES                          # financial result is small; EPS proxy for the dividend
    dps = COMMON["payout"] * eps26                             # FY2026 dividend paid May 2027 (inside the 12 months)
    tp = per_share * (1 + ke) - dps
    return {"pv_explicit": pv.sum(), "tv": tv, "pv_tv": pv_tv, "ev": ev, "net_cash": ncash, "equity": eq,
            "value_per_share": per_share, "dps_next12m": dps, "target": tp, "tv_share_of_ev": pv_tv / ev,
            "t": t, "disc": disc, "pv": pv}


def valuation(ke, g=G_TERM):
    out = {}
    for s in WEIGHTS:
        f = forecast(s)[0]
        out[s] = dcf(f, ke, g)
    tp = sum(WEIGHTS[s] * out[s]["target"] for s in WEIGHTS)
    return out, tp


def rating(tp, price):
    up = tp / price - 1
    return ("Buy" if up >= 0.15 else "Sell" if up <= -0.10 else "Hold"), up


def implied_ke(price, g=G_TERM):
    """Cost of equity at which the probability-weighted 12-month target equals today's price x (1+ke) - dps,
    i.e. today's equity value per share equals the share price (base-case weights)."""
    lo, hi = 0.03, 0.20
    for _ in range(80):
        mid = (lo + hi) / 2
        v = sum(WEIGHTS[s] * dcf(forecast(s)[0], mid, g)["value_per_share"] for s in WEIGHTS)
        lo, hi = (mid, hi) if v > price else (lo, mid)
    return (lo + hi) / 2


def roic_history():
    """ROIC = EBIT x (1 - effective tax rate) / average invested capital; invested capital = equity + pensions
    - cash - deposits/other current financial assets. Cost of capital: year-end Bund + Blume beta x Damodaran ERP
    (January of the following year)."""
    H = history()
    dep = H.loc["Other current financial assets"].fillna(0) + H.loc["Fixed deposits > 3 months"].fillna(0)
    ic = H.loc["Equity"] + H.loc["Pensions"].fillna(0) - H.loc["Cash"] - dep
    nopat = H.loc["EBIT"] * (1 + H.loc["Income taxes"] / H.loc["EBT"])
    roic = nopat / ((ic + ic.shift(1).fillna(ic)) / 2)
    b = pd.read_csv(DATA / "market" / "bund10y_bundesbank_daily.csv", header=None, encoding="utf-8-sig")
    rows = [r for r in b.itertuples(index=False) if str(r[0])[:4].isdigit()]
    bund = pd.Series({pd.Timestamp(r[0]): pd.to_numeric(r[1], errors="coerce") for r in rows}).dropna() / 100
    rf = {y: float(bund.loc[:f"{y}-12-31"].iloc[-1]) for y in HIST}
    e = pd.read_excel(DATA / "market" / "damodaran_ERPbymonth.xlsx", header=0)
    e = e.rename(columns={e.columns[0]: "month"}); e["month"] = pd.to_datetime(e["month"], errors="coerce")
    erp = {y: float(e.loc[e["month"] == pd.Timestamp(f"{y + 1}-01-01"), "ERP (T12 m with sustainable payout)"].iloc[0]) for y in HIST}
    beta = market_inputs()["beta_blume"]
    out = pd.DataFrame({"ic": ic, "nopat": nopat, "roic": roic, "rf": pd.Series(rf), "erp": pd.Series(erp)})
    out["ke"] = out["rf"] + beta * out["erp"]
    return out


def reverse_dcf(price, ke):
    """What the share price requires in the base case at cost of equity ke: (a) the extra annual growth in every region
    in 2027–2030, or (b) the EBIT margin from 2027 onwards, holding everything else at base."""
    import copy

    def value(mod):
        saved = copy.deepcopy(ASSUMPTIONS)
        mod(ASSUMPTIONS["Base"])
        v = dcf(forecast("Base")[0], ke)["value_per_share"]
        ASSUMPTIONS.clear(); ASSUMPTIONS.update(saved)
        return v

    def solve(f, lo, hi):
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) < price else (lo, mid)
        return (lo + hi) / 2

    shift = solve(lambda d: value(lambda a: a.__setitem__("growth_shift", a["growth_shift"] + d)), 0.0, 0.3)
    margin = solve(lambda m: value(lambda a: a.__setitem__("margin", {2026: a["margin"][2026], 2027: m, "later": m})), 0.2, 0.7)
    return {"growth_shift_2027_2030": shift, "ebit_margin_2027_on": margin}


if __name__ == "__main__":
    mk = market_inputs()
    print(json.dumps(mk, indent=1))
    vals, tp = valuation(mk["ke"])
    for s, v in vals.items():
        print(s, {k: round(v[k], 1) for k in ["ev", "equity", "value_per_share", "target", "tv_share_of_ev"]})
    print("weighted TP", round(tp, 1), rating(tp, mk["price"]), "implied ke", round(implied_ke(mk["price"]), 4))
    print(forecast("Base")[0].round(3).T)
