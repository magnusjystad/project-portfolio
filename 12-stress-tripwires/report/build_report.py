"""Builds report/weekly_check_2026-10-07.pdf from the notebook's outputs."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import pandas as pd

from common.report import Report

D, F = ROOT / "data", ROOT / "report" / "figures"
ASOF = "2026-10-07"
cmw = lambda ws: [w * 28.35 for w in ws]
S = json.load(open(D / "summary.json"))
T = pd.read_csv(D / "thresholds.csv", index_col=0)
C = pd.read_csv(D / f"check_{ASOF}.csv", index_col=0)
E = pd.read_csv(D / "events.csv", index_col=0)
BT = pd.read_csv(D / "backtest_episodes.csv", index_col=0)
COR = pd.read_csv(D / "corrections_to_draft.csv")
I = pd.read_csv(D / "indicators_daily.csv", index_col=0, parse_dates=True)
sc = S["score"]


def fmt(v, unit):
    return {"bp": f"{v:+.0f}bp", "$bn": f"${v:,.2f}bn", "index": f"{v:.1f}", "pp": f"{v * 100:+.0f}bp", "%": f"{v:+.1f}%",
            "$m": f"${v:,.0f}m"}.get(unit, f"{v:.2f}")


LEVEL = {1: lambda r: f"SOFR − IORB {r['level']:+.0f}bp", 2: lambda r: f"${r['level']:.1f}bn",
         3: lambda r: f"{r['level']:.1f} (week before {r['level a week earlier']:.1f})",
         4: lambda r: f"{r['level']:.2f}%, {r['tested value'] * 100:+.0f}bp in 20 days",
         5: lambda r: f"{r['level']:.2f}%, {r['tested value'] * 100:+.0f}bp in 20 days",
         6: lambda r: f"${r['level'] / 1000:.2f}tn, {r['tested value']:+.1f}% w/w",
         7: lambda r: f"${r['level']:,.0f}m (week before ${r['level a week earlier']:,.0f}m)",
         8: lambda r: f"{r['level']:.2f}, {r['tested value']:.1f}% move in 20 days",
         9: lambda r: f"{r['level']:.3f}%", 10: lambda r: f"${r['level']:.2f}, {r['tested value']:+.1f}% in 20 days",
         11: lambda r: f"{r['level']:.2f}"}
THR = {k: (lambda k: lambda: f"near {fmt(T.loc[k, 'near'], T.loc[k, 'unit'])}, fire {fmt(T.loc[k, 'fire'], T.loc[k, 'unit'])}")(k)
       for k in T.index}
THR[3] = lambda: "near 117, fire 130 (set by user)"
THR[9] = lambda: "near 4.05%, fire 4.50% (set by user)"
THR[4] = lambda: f"20-day rise: near +{T.loc[4, 'near'] * 100:.0f}bp, fire +{T.loc[4, 'fire'] * 100:.0f}bp"
THR[5] = lambda: f"20-day widening: near +{T.loc[5, 'near'] * 100:.0f}bp, fire +{T.loc[5, 'fire'] * 100:.0f}bp"
THR[7] = lambda: f"near ${T.loc[7, 'near'] / 1000:,.0f}bn, fire ${T.loc[7, 'fire'] / 1000:,.0f}bn"
THR[8] = lambda: f"20-day move: near {T.loc[8, 'near']:.1f}%, fire {T.loc[8, 'fire']:.1f}%"
THR[10] = lambda: f"20-day rise: near +{T.loc[10, 'near']:.0f}%, fire +{T.loc[10, 'fire']:.0f}%"
THR[6] = lambda: f"weekly fall: near {T.loc[6, 'near']:.1f}%, fire {T.loc[6, 'fire']:.1f}%"

rows = []
for k, r in C.iterrows():
    rows.append([str(k), r["tripwire"], f"{LEVEL[k](r)} ({pd.Timestamp(r['date']):%d %b})", THR[k](), r["status"]])
for k, r in E.iterrows():
    rows.append([str(k), r["tripwire"], r["evidence"], r["rule"], r["status"]])
SC = pd.DataFrame(rows, columns=["#", "Tripwire", "Latest (date)", "Trigger", "Status"])
SC["Status"] = SC["Status"].map(lambda s: f"<b>{s}</b>" if s in ("near", "FIRED") else s)

r = Report(ROOT / "report" / f"weekly_check_{ASOF}.pdf", "Market Stress Tripwires: Weekly Check, 7 October 2026",
           "Investment Research Portfolio · Project 16 · market data to the close of 6 October 2026 · monitoring, not financial advice")
verdict = "bending, not breaking" if sc["fired"] == 0 else ("stress building" if sc["fired"] < 3 else "breaking")
r.h1("Verdict")
r.abstract(
    f"<b>{sc['fired']} of {sc['total']} tripwires fired; {sc['near']} are near their line. Verdict: {verdict}.</b> "
    f"The one market tripwire near its line is the Japanese 30-year yield (4.168% on 6 Oct, against a near line of 4.05% and a "
    f"4.5% trigger). Rates volatility rose but stayed well short: MOVE closed at 113.6 on 5 Oct and 105.2 on 6 Oct, against a "
    f"130 trigger. The US 30-year yield rose {C.loc[4, 'tested value'] * 100:.0f}bp in 20 trading days to {C.loc[4, 'level']:.2f}%, "
    f"below the +{T.loc[4, 'near'] * 100:.0f}bp near line. Equity volatility (VIX {C.loc[11, 'level']:.2f}) and funding "
    f"(SOFR at IORB, no repo facility use) are calm. Three event tripwires are near: private credit defaults are at a "
    f"record (Fitch, 6.3% in August); the five largest non-traded private credit funds prorated Q3 redemptions to their 5% cap; and AM "
    f"Best cut two A-CAP life insurers to C+. None has fired.")

r.h1("1. Scorecard")
r.table(SC, caption="Table 1. All 17 tripwires. Market tripwires (1–11) use the last complete session before 7 Oct; "
        "event tripwires (12–17) use news to 7 Oct. Triggers for 1–11 come from each series' own history (section 2).",
        index=False, col_widths=cmw([0.8, 3.5, 5.5, 5.0, 1.3]), font=6.6)
r.image(F / "fig_distance.png", 16.0, "Figure 1. Where each market tripwire sits between its historical median (0) and its "
        "fire trigger (1).")

r.h1("2. What changed this week")
r.bullets([
    f"<b>Bond market:</b> MOVE rose from 101.8 (28 Sep) to 113.6 (5 Oct) before falling back to 105.2. The 5 Oct close was "
    f"the highest since 115.0 on 26 Mar 2026. The US 30-year yield reached 5.66% on 5 Oct and closed at 5.64% on 6 Oct; the "
    f"10-year was 5.27%.",
    "<b>Japan:</b> the 30-year JGB yield reached 4.168% on 6 Oct (Ministry of Finance), up 16bp from 4.009% a month earlier. "
    "Live quotes on 7 Oct were about 4.21–4.23%, which MoF will publish the next day.",
    f"<b>Credit:</b> the US high-yield spread was {C.loc[5, 'level']:.2f}% on 6 Oct, down from 3.24% on 1 Oct but up "
    f"{C.loc[5, 'tested value'] * 100:.0f}bp over 20 days.",
    "<b>Positioning:</b> leveraged funds' Treasury futures shorts were $1.079tn on 29 Sep, down 1.1% from $1.090tn. That is "
    "far from the −8.8% weekly fall that marks the near line.",
    "<b>Oil:</b> Brent front-month futures were $100.58 on 6 Oct, about flat on the month. Dated Brent spot (EIA) was much "
    "higher at $125.44. The physical market is tight while US–Iran talks have not reopened the Strait of Hormuz, and three "
    "tankers were struck near Hormuz on 4–5 Oct.",
    "<b>Private credit:</b> Q3 redemption requests were 11.5–16.8% of shares at the five largest non-traded funds, all paid at "
    "the 5% cap. KKR's K-FITS met 5.06% in full. No fund suspended its tender.",
])
r.image(F / "fig_slow_fast.png", 16.0, "Figure 2. Slow and fast gauges, August to October 2026.")

r.h1("3. Next two weeks (verified dates)")
r.bullets([
    "Treasury auctions: 3-year on 6 Oct, 10-year on 7 Oct, 30-year on 8 Oct (all settle 15 Oct). Watch the tails given MOVE.",
    "Q3 bank earnings begin with JPMorgan on 13 Oct.",
    "Fitch's September private credit default rate, normally mid-October. A reading at least 0.5pp above August's 6.3% fires "
    "tripwire 12.",
    "CFTC Traders in Financial Futures every Friday (positions as of Tuesday).",
    "Just after the window: CoreWeave's DDTL 3.0 equity-cure right expires 28 Oct; FOMC 27–28 Oct (futures price about an "
    "18–20% chance of a hike); UK Budget 28 Oct; BoE decision 5 Nov (a hike about 85% priced); month-end repo; the "
    "continuing resolution expires 11 Dec; the SEC cash-Treasury clearing deadline is 31 Dec 2026.",
])

r.h1("4. Method")
r.p(f"<b>Market tripwires (1–11).</b> Each trigger comes from the series' own history up to 31 Dec 2025, so 2026 is out of "
    f"sample. <i>near</i> = 95th percentile and <i>fire</i> = 99th percentile of daily values (5th and 1st for the weekly change "
    f"in leveraged funds' shorts). Level gauges (SOFR − IORB, repo facility use, swap lines, VIX) are tested on their level. "
    f"Trending series are tested on their speed: the change over 20 observations (US 30-year yield, HY spread, Brent), or "
    f"the absolute move either way (USD/JPY). The user set two triggers, MOVE 130 and JGB 30-year 4.5%; for those, near "
    f"means within 10% of the trigger. Under this rule each tripwire is at or beyond its fire line on about 1% of historical "
    f"days. The exceptions are MOVE, where 130 was exceeded on 8.5% of days, and the JGB 30-year, which has never reached "
    f"4.5%. <b>Event tripwires (12–17)</b> have the written rules shown in Table 1. They are checked against news sources "
    f"listed in data/events.csv.")
bt = BT.copy()
bt.index.name = "Episode"
r.table(bt, caption=f"Table 2. Back-test: tripwires at fire or near status in the two weeks ending on each date. At least one "
        f"market tripwire fired on {S['frequency']['Share with at least one fired']:.0%} of business days since 2007, three or more "
        f"on {S['frequency']['Share with three or more fired']:.1%}.", col_widths=cmw([5.4, 1.4, 1.4, 2.6, 2.4]), font=7.5)
r.image(F / "fig_history.png", 16.5, "Figure 3. Monthly maximum status of each market tripwire since 2007.")
r.p("The back-test shows what the tripwires can and cannot do. MOVE, VIX and USD/JPY caught the large shocks (2008, Covid, "
    "the gilt crisis, SVB, the yen carry unwind and the April 2025 tariffs), and SOFR − IORB caught the September 2019 repo "
    "spike. The 2013 taper tantrum, the 2015 devaluation and the February 2018 volatility spike reached only near status. "
    "The repo facility tripwire has been near or fired at most quarter-ends since 2024, because usage there is routine.")

r.h1("5. Corrections to the 7 October draft")
cor = COR.copy()
r.table(cor, caption="Table 3. Each figure in the draft note checked against its primary source.", index=False,
        col_widths=cmw([2.6, 4.6, 7.2, 2.4]), font=6.5)

r.h1("6. Limitations")
r.bullets([
    "<b>Thresholds are statistical, not causal.</b> A 99th percentile is rare by construction, not necessarily dangerous. "
    "Swap lines fire only at 2008- or 2020-scale usage ($475bn).",
    "<b>Short histories.</b> FRED carries only three years of the HY spread (ICE licensing). The repo facility dates from "
    "July 2021 and SOFR from April 2018.",
    "<b>Data timing.</b> USD/JPY (Fed H.10) lags by several days, and MoF publishes JGB yields the next day. MOVE comes "
    "from Yahoo Finance, and its daily values differ slightly from some other vendors.",
    "<b>Event tripwires depend on news search.</b> Several pages were paywalled or blocked, so some items rest on search "
    "excerpts and syndicated reports (noted in data/events.csv). 'None found' is not proof that nothing happened.",
])
r.p("<b>Sources.</b> NY Fed (SOFR, repo operations); Federal Reserve via FRED (IORB, IOER, H.4.1 swap lines, H.10 USD/JPY, "
    "VIX, Treasury yields, ICE BofA HY OAS, EIA Brent spot); CFTC Traders in Financial Futures; Ministry of Finance Japan; "
    "Yahoo Finance (MOVE, Brent futures); Bloomberg, Reuters, CNBC, Banking Dive, FDIC, Federal Register, SIFMA, AM Best via "
    "InsuranceNewsNet, Iran International, US Treasury and JPMorgan IR for events and dates.")
print("pages:", r.build())
