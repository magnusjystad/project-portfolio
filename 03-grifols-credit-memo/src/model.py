"""Grifols credit model: capital structure, bond yields, 2026–2028 projections, 2028 recovery waterfall, relative value.
Python reference for the Excel workbook (src/build_workbook.py). Assumptions are marked ASSUMPTION and justified in the memo.
"""
import json
from datetime import date
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
VAL = date(2026, 10, 7)
SETTLE = date(2026, 10, 9)
EURUSD_JUN = 1995 / 1751.0           # implied by the H1 2026 note (USD 1,995m = EUR 1,751m)

# ---------------------------------------------------------------------------------------------------------------------
# Capital structure at 30 June 2026 (H1 2026 report, note 14; prices: see data/market/bond_quotes.csv)
CAP = pd.DataFrame([
    # name, EUR m, coupon / margin, maturity, security, rank, price, price source
    ["Revolving credit facility (USD 2,065m)", 351.0, "SOFR + 2.00%", "2032-10-14", "Senior secured", 1, None, "not quoted"],
    ["Term Loan B (USD 1,995m)", 1751.0, "SOFR + 2.50%", "2033-04-14", "Senior secured", 1, None, "not quoted"],
    ["Term Loan B (EUR)", 1250.0, "Euribor + 3.00%", "2033-04-14", "Senior secured", 1, None, "not quoted"],
    ["7.500% senior secured notes", 800.0, "7.500%", "2030-05-01", "Senior secured", 1, 104.25, "TRADEcho via finanzen.net, 19 May 2026"],
    ["7.125% senior secured notes", 1300.0, "7.125%", "2030-05-01", "Senior secured", 1, 104.10, "TRADEcho via finanzen.net, 19 Jun 2026"],
    ["3.875% senior unsecured notes", 1400.0, "3.875%", "2028-10-15", "Senior unsecured", 2, 97.47, "Börse Frankfurt, 7 Oct 2026"],
    ["4.750% senior unsecured notes (USD 705m)", 705 / EURUSD_JUN, "4.750%", "2028-10-15", "Senior unsecured", 2, None, "not quoted"],
    ["Other loans", 125.0, "various", "various", "Unsecured", 2, None, "—"],
    ["Other financial liabilities (mainly GIC agreement)", 835.0, "—", "—", "Unsecured", 2, None, "—"],
    ["Lease liabilities (IFRS 16)", 1045.0, "—", "—", "Leases", 2, None, "—"],
], columns=["Instrument", "Amount (EUR m)", "Coupon", "Maturity", "Security", "Rank", "Price", "Price source"])
CASH_JUN26 = 513.0
RCF_COMMIT_EUR = 2065 / EURUSD_JUN
SECURED_NOTES = 2100.0
TLB = 1751.0 + 1250.0
UNSEC_NOTES = 1400.0 + 705 / EURUSD_JUN
OTHER_UNSEC = 125.0 + 835.0          # other loans + other financial liabilities (GIC agreement EUR 686m and others)

# Reported EBITDA -> Adjusted EBITDA as per Credit Agreement, LTM Q2 2026 (H1 2026 results, annex "Leverage Ratio as per
# Credit Agreement")
EBITDA_BRIDGE = {"Reported EBITDA (EBIT 1,202 + D&A 443)": 1645.0, "IFRS 16 (lease payments deducted)": -120.0,
                 "Restructuring costs": 35.0, "Impairments and others": 99.0, "Transaction costs": 30.0,
                 "Run-rate cost savings, operating improvements and synergies (next 12 months)": 169.0,
                 "Share of profits of associates (core activity)": 4.0}
EBITDA_CA_LTM = 1863.0
ND_CA_JUN26 = 7798.0
ND_BS_JUN26 = 8843.0                 # balance-sheet net financial debt incl. leases
EBITDA_REPORTED_LTM = 1645.0
# NCI contributions, LTM Q2 2026 (H1 2026 results, annex "NCI Contributions"): credit-agreement EBITDA and net financial debt
# of the four subsidiaries with minority owners, and the minority share
NCI = pd.DataFrame({"EBITDA (Credit Agreement)": [118.0, -46.0, 37.0, 24.0],
                    "Net financial debt (Credit Agreement)": [-1148.0, 767.0, -18.0, -29.0],
                    "Minority share": [0.45, 0.192, 1.0, 1.0]},
                   index=["GDS (45% SRAAS)", "Biotest (19.2% others)", "BPC Plasma (100% Scranton)", "Haema (100% Scranton)"])


def proportionate_leverage():
    """Leverage on Grifols' economic share: remove the minorities' share of EBITDA and of net debt."""
    e = EBITDA_CA_LTM - (NCI["EBITDA (Credit Agreement)"] * NCI["Minority share"]).sum()
    nd = ND_CA_JUN26 - (NCI["Net financial debt (Credit Agreement)"] * NCI["Minority share"]).sum()
    return {"EBITDA": e, "Net debt": nd, "Leverage": nd / e}


# ---------------------------------------------------------------------------------------------------------------------
# Bond analytics
def _schedule(maturity, coupon, freq=2):
    m = pd.Timestamp(maturity)
    dates = []
    d = m
    while d.date() > SETTLE:
        dates.append(d.date())
        d = d - pd.DateOffset(months=12 // freq)
    return sorted(dates), d.date()


def yield_to(price, coupon, maturity, redemption=100.0, end=None, freq=2):
    """Yield (annual, compounded `freq` times a year) from clean price, coupon (%), to `end` (call date) at `redemption`."""
    sched, prev = _schedule(maturity, coupon, freq)
    end = end or pd.Timestamp(maturity).date()
    flows = [d for d in sched if d <= end]
    if not flows or flows[-1] != end:
        flows.append(end)
    nxt = sched[0]
    period = (nxt - prev).days
    accrued = coupon / freq * (SETTLE - prev).days / period
    dirty = price + accrued
    c = coupon / freq

    def pv(y):
        tot = 0.0
        for d in flows:
            k = sum(1 for x in sched if x < d)             # whole coupon periods after the next coupon date (ISMA)
            t = (min(d, nxt) - SETTLE).days / period + k
            cf = c if d in sched else c * (d - max([prev] + [s for s in sched if s < d])).days / period
            if d == end:
                cf += redemption
            tot += cf / (1 + y / freq) ** t
        return tot
    lo, hi = -0.5, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if pv(mid) > dirty else (lo, mid)
    y = (lo + hi) / 2
    return (1 + y / freq) ** freq - 1, accrued              # annual-equivalent (ISMA) yield, as quoted by Börse Frankfurt


CALLS = {"7.125% senior secured notes": [("2026-10-24", 104.0), ("2027-05-01", 102.0), ("2028-05-01", 100.0)],   # indenture s.3.07
         "7.500% senior secured notes": [("2026-10-24", 104.0), ("2027-05-01", 102.0), ("2028-05-01", 100.0)],   # aligned by Nov 2025 consent
         "3.875% senior unsecured notes": [("2026-10-24", 100.0)]}                                                 # callable at par from 15 Oct 2026


@lru_cache(maxsize=None)
def bond_yields():
    rows = {}
    for name in ["7.500% senior secured notes", "7.125% senior secured notes", "3.875% senior unsecured notes"]:
        r = CAP.set_index("Instrument").loc[name]
        cpn = float(r["Coupon"].rstrip("%"))
        ytm, acc = yield_to(r["Price"], cpn, r["Maturity"])
        cands = [("maturity " + r["Maturity"], ytm)]
        for d, px in CALLS.get(name, []):
            y, _ = yield_to(r["Price"], cpn, r["Maturity"], redemption=px, end=pd.Timestamp(d).date())
            cands.append((f"call {d} at {px:g}", y))
        worst = min(cands, key=lambda x: x[1])
        rows[name] = {"price": r["Price"], "coupon": cpn, "ytm": ytm, "ytw": worst[1], "worst": worst[0], "accrued": acc,
                      "candidates": cands}
    return rows


@lru_cache(maxsize=None)
def bund_curve():
    """Bundesbank yields on listed federal securities by residual maturity (1–4 years, Svensson) on 7 Oct 2026."""
    out = {}
    for m, yrs in [("R01XX", 1), ("R02XX", 2), ("R03XX", 3), ("R04XX", 4)]:
        rows = [l.split(",") for l in open(DATA / "market" / f"bund_svensson_{m}.csv", encoding="utf-8-sig").read().splitlines() if l[:4].isdigit()]
        s = pd.Series({pd.Timestamp(r[0]): pd.to_numeric(r[1], errors="coerce") for r in rows}).dropna()
        out[yrs] = float(s.loc[:pd.Timestamp(VAL)].iloc[-1]) / 100
    return out


def bund_at(years):
    c = bund_curve()
    xs = sorted(c)
    return float(np.interp(years, xs, [c[x] for x in xs]))


def hy_oas():
    d = pd.read_csv(DATA / "market" / "fred_BAMLHE00EHYIOAS.csv", index_col=0, parse_dates=True).iloc[:, 0].dropna()
    return float(d.loc[:pd.Timestamp(VAL)].iloc[-1]) / 100, str(d.loc[:pd.Timestamp(VAL)].index[-1].date())


def sp_default():
    """S&P 2024 Annual Global Corporate Default and Rating Transition Study (27 Mar 2025), table 'Global corporate average
    cumulative default rates by rating level, 1981-2024': BB- row."""
    return {"rating": "BB-", "y1": 0.0087, "y2": 0.0271, "y3": 0.0462}


# ---------------------------------------------------------------------------------------------------------------------
# Projections (ASSUMPTIONS, see memo section 5)
BASE = {"rev_growth": {2026: 0.000, 2027: 0.05, 2028: 0.05}, "margin": {2026: 0.250, 2027: 0.255, 2028: 0.260}}
DOWNSIDE_BPS = 0.03                    # brief: EBITDA margin 300bp lower (applied to H2 2026, 2027, 2028)
PLASMA_SHARE_OF_COGS = None            # not disclosed by Grifols; see plasma_equivalence()
COGS_PCT_REV = 4665 / 7524             # 2025 cost of sales / revenue (FY2025 income statement): 62.0%
CA_UPLIFT = 27.0                       # Credit-agreement EBITDA − Adjusted EBITDA, FY2025 (1,852 − 1,825)
FCF_ITEMS = {"capex_it_rd": 530.0, "taxes": 170.0, "nwc": 60.0, "others": 70.0}   # 2025: 531, 169, 67, 69 (FCF bridge)
DIVIDENDS = 128.0                      # 2025 cash dividends (cash flow statement)
SOFR, EURIBOR = 0.039, 0.0264          # FRED SOFR 6 Oct 2026; ECB 3M Euribor Sep 2026


def cash_interest(rcf_drawn=351.0):
    usd_tlb = 1751.0 * (SOFR + 0.025)
    eur_tlb = 1250.0 * (EURIBOR + 0.03)
    rcf = rcf_drawn * (SOFR + 0.02) + (RCF_COMMIT_EUR - rcf_drawn) * 0.0035       # ASSUMPTION: 35bp commitment fee
    notes = 800 * 0.075 + 1300 * 0.07125 + 1400 * 0.03875 + 705 / EURUSD_JUN * 0.0475
    other = 0.05 * OTHER_UNSEC                                                    # ASSUMPTION: 5% on other loans/liabilities
    return usd_tlb + eur_tlb + rcf + notes + other


def project(downside=False):
    rev, ebitda, rows = 7524.0, None, {}
    nd = 7759.0                                         # net financial debt (credit agreement), 31 Dec 2025
    for y in (2026, 2027, 2028):
        rev = rev * (1 + BASE["rev_growth"][y])
        m = BASE["margin"][y] - (DOWNSIDE_BPS * (0.5 if y == 2026 else 1.0) if downside else 0.0)
        e = rev * m
        intr = cash_interest()
        fcf = e - intr - sum(FCF_ITEMS.values())
        nd = nd - (fcf - DIVIDENDS)
        ca = e + CA_UPLIFT
        rows[y] = {"Revenue": rev, "EBITDA margin": m, "Adjusted EBITDA": e, "Cash interest": intr,
                   "Capex, IT & R&D": FCF_ITEMS["capex_it_rd"], "Taxes": FCF_ITEMS["taxes"], "Working capital": FCF_ITEMS["nwc"],
                   "Other": FCF_ITEMS["others"], "FCF pre-dividends": fcf, "Dividends": DIVIDENDS,
                   "Net debt (Credit Agreement)": nd, "Credit-agreement EBITDA": ca, "Net leverage (x)": nd / ca,
                   "EBITDA / cash interest (x)": e / intr}
    return pd.DataFrame(rows)


def plasma_equivalence():
    """Plasma share of cost of sales at which a 10% rise in plasma cost per litre equals the 300bp margin hit."""
    return DOWNSIDE_BPS / (0.10 * COGS_PCT_REV)


# ---------------------------------------------------------------------------------------------------------------------
# Recovery waterfall (default in 2028)
ADMIN = 0.05                         # ASSUMPTION: administrative claims 5% of enterprise value
MULTIPLE = 6.0                       # brief


def waterfall(ebitda_2028, multiple=MULTIPLE, admin=ADMIN, rcf_draw=0.80):
    ev = ebitda_2028 * multiple
    left = ev * (1 - admin)
    secured = TLB + rcf_draw * RCF_COMMIT_EUR + SECURED_NOTES
    sec_rec = min(1.0, left / secured)
    left -= min(left, secured)
    deficiency = secured * (1 - sec_rec)
    unsecured_claims = UNSEC_NOTES + OTHER_UNSEC + deficiency       # secured deficiency claims share with unsecured
    uns_rec = min(1.0, left / unsecured_claims) if unsecured_claims else 0
    return {"EV": ev, "Admin claims": ev * admin, "Secured claims": secured, "Secured recovery": sec_rec,
            "Unsecured claims": unsecured_claims, "Unsecured recovery": uns_rec,
            "Residual to equity": max(0.0, left - unsecured_claims)}


def refinancing(df):
    """Leverage and liquidity at the October 2028 unsecured maturity (interpolated 10/12 of the way through 2028).
    RCF: USD 2,065m, springs to 91 days before any unrefinanced material maturity (20-F 2025, Item 5), i.e. mid-July 2028,
    so the 2028 notes must be refinanced or repaid before then."""
    nd27, nd28 = df.loc["Net debt (Credit Agreement)", 2027], df.loc["Net debt (Credit Agreement)", 2028]
    e27, e28 = df.loc["Credit-agreement EBITDA", 2027], df.loc["Credit-agreement EBITDA", 2028]
    w = 10 / 12
    nd, e = nd27 + w * (nd28 - nd27), e27 + w * (e28 - e27)
    nd_jun26 = 7798.0                                    # net financial debt (credit agreement), 30 June 2026
    retained = nd_jun26 - nd                             # FCF after dividends, Jul 2026 – Oct 2028 (net debt path)
    available = CASH_JUN26 + (RCF_COMMIT_EUR - 351.0) + retained
    return {"Net debt Oct 2028": nd, "Credit-agreement EBITDA (LTM Oct 2028)": e, "Net leverage Oct 2028 (x)": nd / e,
            "Unsecured notes due Oct 2028": UNSEC_NOTES, "Cash + undrawn RCF, 30 Jun 2026": CASH_JUN26 + RCF_COMMIT_EUR - 351.0,
            "FCF after dividends, Jul 2026 – Oct 2028": retained, "Liquidity available before maturity": available,
            "Liquidity / notes due (x)": available / UNSEC_NOTES, "Leverage at or below 3.5x target": bool(nd / e <= 3.5)}

def recovery_grid(ebitda, multiples=(3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5)):
    return pd.DataFrame({m: {"EV": ebitda * m, "Secured": waterfall(ebitda, m)["Secured recovery"],
                             "Unsecured": waterfall(ebitda, m)["Unsecured recovery"]} for m in multiples})


def breakeven_multiple(ebitda, which):
    """Lowest EV/EBITDA multiple at which the tranche still recovers 100%."""
    lo, hi = 0.0, 20.0
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if waterfall(ebitda, mid)[which] < 1 - 1e-12 else (lo, mid)
    return hi


def price_for_yield(name, target):
    """Clean price of the secured 2030 notes at which their yield-to-worst equals `target`."""
    r = CAP.set_index("Instrument").loc[name]
    cpn = float(r["Coupon"].rstrip("%"))

    def ytw(px):
        ys = [yield_to(px, cpn, r["Maturity"])[0]] + [yield_to(px, cpn, r["Maturity"], redemption=c, end=pd.Timestamp(d).date())[0]
                                                    for d, c in CALLS[name]]
        return min(ys)
    lo, hi = 80.0, 110.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ytw(mid) > target else (lo, mid)
    return (lo + hi) / 2


# ---------------------------------------------------------------------------------------------------------------------
def relative_value(rec_sec, rec_uns):
    B = bond_yields()
    pd_ = sp_default()["y3"]
    sec, uns = B["7.125% senior secured notes"], B["3.875% senior unsecured notes"]
    def years(worst):                              # years from settlement to the worst-case redemption date
        return (pd.Timestamp(worst.split()[1]).date() - SETTLE).days / 365.25
    yrs_sec, yrs_uns = years(sec["worst"]), years(uns["worst"])
    out = {}
    for name, b, yrs, rec, lev in [("7.125% secured 2030", sec, yrs_sec, rec_sec, 4939.0 / EBITDA_CA_LTM), ("3.875% unsecured 2028", uns, yrs_uns, rec_uns, ND_CA_JUN26 / EBITDA_CA_LTM)]:
        bund = bund_at(yrs)                          # flat below 1 year
        spread = b["ytw"] - bund
        el = pd_ * (1 - rec)                           # brief: expected return = yield − PD × (1 − recovery)
        out[name] = {"price": b["price"], "YTW": b["ytw"], "worst": b["worst"], "YTM": b["ytm"], "years to worst": yrs,
                     "Bund (matched)": bund, "spread": spread, "leverage through tranche (x)": lev,
                     "spread per turn (bp)": spread * 1e4 / lev, "recovery": rec, "PD (3y cumulative)": pd_,
                     "expected loss": el, "expected return": b["ytw"] - el}
    return pd.DataFrame(out)


def gap_at_multiple(ebitda, m):
    w = waterfall(ebitda, m)
    rv = relative_value(w["Secured recovery"], w["Unsecured recovery"])
    return rv.loc["expected return", "7.125% secured 2030"] - rv.loc["expected return", "3.875% unsecured 2028"]


def multiple_for_gap(ebitda, target):
    """EV/EBITDA multiple at which (secured − unsecured) expected return equals `target` (gap falls as the multiple rises)."""
    lo, hi = 2.0, 6.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if gap_at_multiple(ebitda, mid) > target else (lo, mid)
    return (lo + hi) / 2


def run():
    base, down = project(False), project(True)
    w_base = waterfall(base.loc["Adjusted EBITDA", 2028])
    w_down = waterfall(down.loc["Adjusted EBITDA", 2028])
    rv = relative_value(w_down["Secured recovery"], w_down["Unsecured recovery"])
    gap = rv.loc["expected return", "7.125% secured 2030"] - rv.loc["expected return", "3.875% unsecured 2028"]
    if abs(gap) < 0.005:
        rec = "Neutral on both (gap under 50bp)"
    else:
        rec = ("Overweight the 7.125% secured 2030s, Underweight the 3.875% unsecured 2028s" if gap > 0
               else "Overweight the 3.875% unsecured 2028s, Underweight the 7.125% secured 2030s")
    return {"base": base, "down": down, "w_base": w_base, "w_down": w_down, "rv": rv, "gap": gap, "rec": rec,
            "yields": bond_yields(), "hy_oas": hy_oas(), "sp": sp_default(), "plasma_eq": plasma_equivalence(),
            "bund": bund_curve(), "prop": proportionate_leverage(), "refi_base": refinancing(base), "refi_down": refinancing(down),
            "grid": recovery_grid(down.loc["Adjusted EBITDA", 2028]),
            "be_sec": breakeven_multiple(down.loc["Adjusted EBITDA", 2028], "Secured recovery"),
            "be_uns": breakeven_multiple(down.loc["Adjusted EBITDA", 2028], "Unsecured recovery"),
            "px_neutral": price_for_yield("7.125% senior secured notes", rv.loc["expected return", "3.875% unsecured 2028"] - 0.005),
            "m_flip": multiple_for_gap(down.loc["Adjusted EBITDA", 2028], 0.0),
            "m_neutral": multiple_for_gap(down.loc["Adjusted EBITDA", 2028], -0.005),
            "px_flip": price_for_yield("7.125% senior secured notes", rv.loc["expected return", "3.875% unsecured 2028"])}


if __name__ == "__main__":
    R = run()
    pd.set_option("display.width", 200)
    for k in ["base", "down"]:
        print(k); print(R[k].round(3))
    print(json.dumps({k: R[k] for k in ["w_base", "w_down"]}, indent=1, default=float))
    print(R["rv"].round(4))
    print("gap", round(R["gap"] * 1e4, 1), "bp ->", R["rec"])
    print(R["refi_base"]); print(R["refi_down"]); print(R["grid"].round(3)); print(R["be_sec"], R["be_uns"], R["px_neutral"], R["px_flip"], R["m_flip"], R["m_neutral"])
    print({k: (v["ytw"], v["worst"], v["ytm"]) for k, v in R["yields"].items()}, R["hy_oas"], R["bund"], round(R["plasma_eq"], 3))
