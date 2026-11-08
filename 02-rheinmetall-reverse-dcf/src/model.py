"""Rheinmetall reverse DCF (Python reference; the Excel workbook reproduces it with formulas).

Value = PV of FCFF (H2 2026–2035) + Gordon terminal value at 31 Dec 2035, discounted at WACC, less the claims in the
bridge from enterprise value to equity value at 30 June 2026. Sales start from 2025 continuing operations (€9,935m).
"""
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
import sys  # noqa: E402
sys.path[:0] = [str(ROOT)]
DATA = ROOT / "data"
PUB = pd.Timestamp("2026-10-07")
YEARS = list(range(2026, 2036))
G_TERM = 0.02
SALES_2025 = 9935.0             # € m, continuing operations (AR 2025)
MARGIN_2025 = 0.185             # operating result margin 2025 (AR 2025)
MGMT = {"sales_2030": 50000.0, "margin_2030": 0.20, "ccr": 0.50, "sales_2026": 13950.0}   # CMD 2025 / Sept 2026 IR deck
SHARES_ISSUED = 46_777_223      # 30 June 2026, after conversions (H1 2026 report)
TREASURY = 121_504              # 31 Dec 2025 (AR 2025, Rheinmetall AG)
BRIDGE = {  # € m at 30 June 2026 (H1 2026 report, balance sheet), sign = effect on equity value
    "Net financial debt (continuing operations)": -2722.0,
    "Pension provisions": -295.0,
    "Non-controlling interests (book value)": -797.0,
    "Investments accounted for using the equity method (book value)": 284.0,
    "Net assets held for sale (civilian business, book value: 1,146 − 733)": 1146.0 - 733.0,
}
GROSS_DEBT = 1238.0 + 1740.0 + 295.0   # non-current + current financial debts + pensions, 30 June 2026


# ---------------------------------------------------------------------------------------------------------------------
def history():
    return pd.read_csv(DATA / "history.csv", index_col=0).rename(columns=int)


def tax_rate():
    """Average 2023–2025 effective tax rate on continuing operations: (EBT − earnings from continuing ops) / EBT."""
    ebt = {2023: 815.0, 2024: 1168.0, 2025: 1572.0}              # AR 2025 key figures
    earn = {2023: 630.0, 2024: 840.0, 2025: 1176.0}
    return float(np.mean([(ebt[y] - earn[y]) / ebt[y] for y in ebt]))


def bond_ytm(price, settle=date(2026, 10, 9), coupon=3.375, maturity=date(2031, 5, 28)):
    """Annual-coupon yield to maturity from a clean price (ACT/ACT accrual, standard street convention)."""
    cfs = [(date(y, 5, 28), coupon + (100 if y == maturity.year else 0)) for y in range(2027, maturity.year + 1)]
    last = date(2026, 5, 28)
    accrued = coupon * (settle - last).days / (cfs[0][0] - last).days
    dirty = price + accrued
    frac = (cfs[0][0] - settle).days / (cfs[0][0] - last).days

    def pv(y):
        return sum(cf / (1 + y) ** (frac + i) for i, (_, cf) in enumerate(cfs))
    lo, hi = 0.0, 0.2
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if pv(mid) > dirty else (lo, mid)
    return (lo + hi) / 2, accrued


def market_inputs():
    b = pd.read_csv(DATA / "market" / "bund10y_bundesbank_daily.csv", header=None, encoding="utf-8-sig")
    rows = [r for r in b.itertuples(index=False) if str(r[0])[:4].isdigit()]
    bund = pd.Series({pd.Timestamp(r[0]): pd.to_numeric(r[1], errors="coerce") for r in rows}).dropna() / 100
    rf = float(bund.loc[:PUB].iloc[-1])
    e = pd.read_excel(DATA / "market" / "damodaran_ERPbymonth.xlsx", header=0)
    e = e.rename(columns={e.columns[0]: "month"}); e["month"] = pd.to_datetime(e["month"], errors="coerce")
    erp = float(e.loc[e["month"] <= PUB].iloc[-1]["ERP (T12 m with sustainable payout)"])
    adj = pd.read_csv(DATA / "market" / "prices_adj_daily.csv", index_col=0, parse_dates=True)
    m = adj[["RHM.DE", "^STOXX"]].resample("ME").last().pct_change().loc["2021-10":"2026-09"].dropna()
    reg = sm.OLS(m["RHM.DE"], sm.add_constant(m["^STOXX"])).fit()
    raw = float(reg.params["^STOXX"]); blume = 0.67 * raw + 0.33
    px = pd.read_csv(DATA / "market" / "prices_daily.csv", index_col=0, parse_dates=True)
    price = float(px.loc[:PUB, "RHM.DE"].dropna().iloc[-1])
    q = pd.read_csv(DATA / "market" / "rheinmetall_bond_quote_2026-10-07.csv").iloc[0]
    ytm, acc = bond_ytm(float(q["last_price"]))
    t = tax_rate()
    shares = (SHARES_ISSUED - TREASURY) / 1e6
    E, Dv = price * shares, GROSS_DEBT
    ke = rf + blume * erp
    wacc = E / (E + Dv) * ke + Dv / (E + Dv) * ytm * (1 - t)
    return {"rf": rf, "erp": erp, "beta_raw": raw, "beta_se": float(reg.bse["^STOXX"]), "beta_r2": float(reg.rsquared),
            "beta_blume": blume, "ke": ke, "bond_price": float(q["last_price"]), "kd": ytm, "accrued": acc, "tax": t,
            "price": price, "shares_m": shares, "mcap": E, "debt": Dv, "w_e": E / (E + Dv), "wacc": wacc}


# ---------------------------------------------------------------------------------------------------------------------
def sales_path_cagr(cagr):
    return pd.Series({y: SALES_2025 * (1 + cagr) ** (y - 2025) for y in YEARS})


def sales_path_target(sales_2030, growth_after):
    """2026 at guidance midpoint, constant growth 2027–2030 to reach sales_2030, then `growth_after` (Series 2031–2035)."""
    g = (sales_2030 / MGMT["sales_2026"]) ** (1 / 4) - 1
    s = {2026: MGMT["sales_2026"]}
    for y in range(2027, 2031):
        s[y] = s[y - 1] * (1 + g)
    for y in range(2031, 2036):
        s[y] = s[y - 1] * (1 + growth_after[y])
    return pd.Series(s)


def margin_path(target):
    """Linear from the 2025 margin to `target` in 2030, flat afterwards."""
    return pd.Series({y: MARGIN_2025 + (target - MARGIN_2025) * min(y - 2025, 5) / 5 for y in YEARS})


def calibrate_k(tax):
    """Sales-to-incremental-capital ratio at which management's own plan (guidance 2026, €50bn and 20% in 2030)
    converts 50% of 2026–2030 operating result into free cash flow, its cash-conversion target."""
    s = sales_path_target(MGMT["sales_2030"], pd.Series({y: 0.0 for y in range(2031, 2036)}))
    m = margin_path(MGMT["margin_2030"])
    yrs = range(2026, 2031)
    ebit = sum(s[y] * m[y] for y in yrs)
    ds = s[2030] - SALES_2025
    # sum NOPAT - dS/k = ccr * sum EBIT  ->  k = dS / ((1 - tax - ccr) * sum EBIT)
    return ds / ((1 - tax - MGMT["ccr"]) * ebit)


def fcff(sales, margin, tax, k):
    ebit = sales * margin
    nopat = ebit * (1 - tax)
    prev = pd.concat([pd.Series({2025: SALES_2025}), sales]).shift(1).loc[YEARS]
    reinv = (sales - prev) / k
    return pd.DataFrame({"Sales": sales, "Growth": sales / prev - 1, "Operating margin": margin, "EBIT": ebit, "NOPAT": nopat,
                         "Reinvestment": -reinv, "FCFF": nopat - reinv})


def value(f, wacc, tax, k, g=G_TERM, shares=None):
    t = pd.Series({y: ((pd.Timestamp("2026-10-01") if y == 2026 else pd.Timestamp(f"{y}-07-01")) - PUB).days / 365.25 for y in YEARS})
    cf = f["FCFF"].copy(); cf[2026] *= 0.5                      # H1 2026 cash flow is already in the 30 June balance sheet
    pv = (cf * (1 + wacc) ** (-t)).sum()
    s36 = f["Sales"][2035] * (1 + g)
    fcf36 = s36 * f["Operating margin"][2035] * (1 - tax) - (s36 - f["Sales"][2035]) / k
    tv = fcf36 / (wacc - g)
    pv_tv = tv * (1 + wacc) ** (-((pd.Timestamp("2035-12-31") - PUB).days / 365.25))
    ev = pv + pv_tv
    eq = ev + sum(BRIDGE.values())
    return {"pv_explicit": pv, "tv": tv, "pv_tv": pv_tv, "ev": ev, "equity": eq, "per_share": eq / shares, "t": t}


def solve(fn, lo, hi, target, n=80):
    for _ in range(n):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if fn(mid) < target else (lo, mid)
    return (lo + hi) / 2


# ---------------------------------------------------------------------------------------------------------------------
# Budget, cases, tests
EUR_SALES_SHARE_2025 = (3774.0 + 4264.0) / 9935.0      # Germany + other Europe, AR 2025 sales by region


def eurusd():
    p = pd.read_csv(DATA / "market" / "eurusd_daily.csv", index_col=0, parse_dates=True)   # yfinance EURUSD=X
    return float(p.loc[:PUB, "EURUSD=X"].dropna().iloc[-1])


def budget():
    from src import nato
    P, C = nato.equipment_path()
    fx = eurusd()
    tot = P.sum() / fx                                        # € m
    growth = tot.pct_change()
    return tot, growth, fx, C


def case_paths(growth):
    after = growth.loc[2031:2035]
    return {"Bear": (sales_path_target(30000.0, after), margin_path(0.15)),
            "Base": (sales_path_target(40000.0, after), margin_path(0.185)),
            "Bull": (sales_path_target(MGMT["sales_2030"], after), margin_path(0.21))}


def run():
    mk = market_inputs()
    k = calibrate_k(mk["tax"])
    tot, growth, fx, C = budget()
    W, T = mk["wacc"], mk["tax"]
    ps = lambda f: value(f, W, T, k, shares=mk["shares_m"])["per_share"]
    # (a) constant 2025-2035 CAGR at management's 20% margin
    a = solve(lambda c: ps(fcff(sales_path_cagr(c), margin_path(MGMT["margin_2030"]), T, k)), -0.05, 0.6, mk["price"])
    # (b) steady-state margin at management's revenue path
    mg_sales = sales_path_target(MGMT["sales_2030"], growth.loc[2031:2035])
    b = solve(lambda m: ps(fcff(mg_sales, margin_path(m), T, k)), -0.2, 0.5, mk["price"])
    cases = case_paths(growth)
    case_val = {n: value(fcff(sp, mp, T, k), W, T, k, shares=mk["shares_m"]) for n, (sp, mp) in cases.items()}
    # grid
    cagrs = np.arange(0.05, 0.2501, 0.025); margins = np.arange(0.10, 0.2001, 0.01)
    grid = pd.DataFrame({round(m, 3): {round(c, 3): ps(fcff(sales_path_cagr(c), margin_path(m), T, k)) for c in cagrs} for m in margins})
    # tests
    imp_sales_2035 = SALES_2025 * (1 + a) ** 10
    share = lambda s35: s35 * EUR_SALES_SHARE_2025 / tot[2035]
    share_today = SALES_2025 * EUR_SALES_SHARE_2025 / tot[2025]
    imp_cum = sum(SALES_2025 * (1 + a) ** (y - 2025) for y in range(2026, 2031))
    tests = {
        "budget": {"implied": share(imp_sales_2035), "today": share_today,
                   **{n: share(cases[n][0][2035]) for n in cases}},
        "backlog": {"implied": imp_cum, **{n: cases[n][0].loc[2026:2030].sum() for n in cases}},
        "margin": {"implied": b, **{n: cases[n][1][2035] for n in cases}},
    }
    # discount-rate dependence: implied CAGR / margin at other WACCs, and the WACC at which each case equals the price
    def implied_at(w):
        psw = lambda f: value(f, w, T, k, shares=mk["shares_m"])["per_share"]
        ca = solve(lambda c: psw(fcff(sales_path_cagr(c), margin_path(MGMT["margin_2030"]), T, k)), -0.05, 0.6, mk["price"])
        mb = solve(lambda m: psw(fcff(mg_sales, margin_path(m), T, k)), -0.2, 0.6, mk["price"])
        return {"implied CAGR 2025-35 (20% margin)": ca, "implied 2035 sales (EUR m)": SALES_2025 * (1 + ca) ** 10,
                "implied margin (mgmt sales path)": mb, **{f"{n} value/share": psw(fcff(*cases[n], T, k)) for n in cases}}
    sens = pd.DataFrame({round(w, 4): implied_at(w) for w in [W, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12]}).T
    irr = {n: solve(lambda w: -value(fcff(*cases[n], T, k), w, T, k, shares=mk["shares_m"])["per_share"], 0.03, 0.40, -mk["price"])
           for n in cases}
    return {"mk": mk, "k": k, "fx": fx, "wacc_sens": sens, "implied_wacc": irr, "budget": tot, "budget_growth": growth, "nato_check": C, "a_cagr": a,
            "a_sales_2035": imp_sales_2035, "b_margin": b, "mgmt_sales": mg_sales, "cases": cases, "case_val": case_val,
            "grid": grid, "tests": tests}


if __name__ == "__main__":
    R = run()
    print(json.dumps({k: v for k, v in R["mk"].items()}, indent=1, default=float))
    print("k", round(R["k"], 2), "fx", R["fx"])
    print("(a) implied CAGR", round(R["a_cagr"], 4), "2035 sales", round(R["a_sales_2035"]), "| (b) implied margin", round(R["b_margin"], 4))
    for n, v in R["case_val"].items():
        print(n, round(v["per_share"], 1), "2030 sales", round(R["cases"][n][0][2030]), "2035 sales", round(R["cases"][n][0][2035]))
    print(json.dumps(R["tests"], indent=1, default=float))
    print(R["grid"].round(0))
    print(R["wacc_sens"].round(3).to_string())
    print("WACC at which each case equals the price:", {k: round(v, 4) for k, v in R["implied_wacc"].items()})
