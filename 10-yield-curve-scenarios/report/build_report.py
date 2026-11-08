"""Builds report/report.pdf from the notebook outputs."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import pandas as pd

from common.report import Report
from yieldcurve.scenarios import DESCR

D, F = ROOT / "data", ROOT / "report" / "figures"
rd = lambda n, **k: pd.read_csv(D / f"{n}.csv", index_col=0, **k)
m = json.load(open(D / "meta.json"))
boot, cmp_, prm = rd("bootstrap_2026-09-30"), rd("nss_vs_gsw"), rd("nss_parameters")
ns, pca, port = rd("ns_daily_factors", parse_dates=True), rd("pca_loadings"), rd("portfolios")
krd, hor, bb = rd("key_rate_durations"), rd("horizon_returns"), rd("barbell_minus_bullet")
pnl = pd.read_csv(D / "scenario_pnl.csv")
par = pd.read_csv(D / "treasury_par_yields_daily.csv", index_col=0, parse_dates=True)
pct = lambda x, d=2: f"{x * 100:.{d}f}%"
ex = m["pca_explained"]
row = par.loc["2026-09-30"]

r = Report(ROOT / "report" / "report.pdf", "A US Treasury Curve Model and Bond Portfolio Scenario Tool",
           "Investment Research Portfolio · Project 11 · Curve date 30 September 2026")
r.h1("Summary")
r.abstract(
    f"I build the US Treasury zero curve on 30 September 2026 from the Treasury's par yields, fit a Nelson-Siegel-Svensson "
    f"(NSS) model that matches the Federal Reserve's Gürkaynak-Sack-Wright (GSW) curve within "
    f"{cmp_['NSS − GSW (bp)'].abs().max():.1f} bp at 2, 5, 10 and 30 years, and track the level, slope and curvature of the "
    f"curve daily since 2006. Three factors explain {pct(sum(ex[:3]),1)} of daily yield changes (level alone {pct(ex[0],1)}). "
    f"I then price a 7-year bullet, a duration-matched 2/30-year barbell and a 1–10-year ladder ($100m each) and revalue "
    f"them under six instant curve scenarios. The barbell gains {bb.max().iloc[0]:.0f} bp more than the bullet in a bull "
    f"flattener and loses {-bb.min().iloc[0]:.0f} bp more in a bear steepener; its extra convexity adds about "
    f"{bb.loc['Parallel +100bp'].iloc[0]:.0f} bp in a ±100 bp parallel move. The price of that convexity is "
    f"{-m['carry_gap_bp']:.0f} bp less 12-month carry and roll-down than the bullet if the curve does not move.")

r.h1("1. Data")
r.bullets([
    "<b>U.S. Treasury Daily Par Yield Curve Rates</b> (home.treasury.gov), January 2006 – 30 September 2026, "
    f"{len(par.loc['2006':'2026-09-30']):,} days. On 30 September 2026 the curve has 14 points from 1 month to 30 years "
    f"(1-month {row['1 Mo']:.2f}%, 2-year {row['2 Yr']:.2f}%, 10-year {row['10 Yr']:.2f}%, 20-year {row['20 Yr']:.2f}%, "
    f"30-year {row['30 Yr']:.2f}%).",
    "<b>Federal Reserve GSW dataset</b> (feds200628.csv, Gürkaynak, Sack and Wright, 2007): fitted Svensson parameters and "
    "continuously compounded zero-coupon yields, used as an independent benchmark.",
    "<b>NBER recession indicator</b> (FRED USREC) for shading.",
])
r.h1("2. Bootstrapping the zero curve")
r.p("Par yields are interpolated with a natural cubic spline onto a semiannual grid from 0.5 to 30 years. Treating each "
    "grid point as a par bond paying semiannual coupons, discount factors are solved sequentially: "
    "d(T) = (1 − c/2·Σ<sub>t&lt;T</sub> d(t)) / (1 + c/2). Between grid points the log discount factor is interpolated "
    f"linearly. The resulting curve reprices every par bond on the grid to within {m['max_boot_error_bp']:.0e} bp.")
bt = boot.loc[[0.5, 1, 2, 3, 5, 7, 10, 20, 30]].copy()
bt = pd.DataFrame({"Par yield": bt["Par (spline)"].map(pct), "Discount factor": bt["Discount factor"].map(lambda x: f"{x:.5f}"),
                   "Zero (semiannual)": bt["Zero (semiannual)"].map(pct), "Zero (continuous)": bt["Zero (continuous)"].map(pct)},
                  index=[f"{x:g}y" for x in bt.index])
bt.index.name = "Maturity"
r.table(bt, caption="Table 1. Bootstrapped curve on 30 September 2026 (selected maturities).")
r.p(f"The 20-year par yield ({row['20 Yr']:.2f}%) is above the 30-year ({row['30 Yr']:.2f}%), a long-standing feature of the "
    "20-year sector. Because the spline must pass through every quote, the bootstrapped zero curve bulges between 15 and "
    "25 years (Figure 1). Bootstrapping is exact but inherits every quirk of the input quotes; a parametric curve smooths them.")
r.h1("3. Nelson-Siegel-Svensson fit and comparison with the Fed curve")
r.p(f"The Svensson (1994) form, z(t) = β0 + β1·L1(t/τ1) + β2·C(t/τ1) + β3·C(t/τ2), is fitted by nonlinear least squares so "
    f"that the model's par yields match the 14 observed par yields (bills on a bond-equivalent basis), from 18 starting "
    f"points with β0 ≥ 0. The fit error is {m['nss_rmse_bp']:.1f} bp root-mean-square.")
pt = prm.copy().astype(object)
pt.loc[["beta0", "beta1", "beta2", "beta3"]] = pt.loc[["beta0", "beta1", "beta2", "beta3"]].map(lambda x: pct(x, 3))
pt.loc[["tau1", "tau2"]] = pt.loc[["tau1", "tau2"]].map(lambda x: f"{float(x):.2f}")
pt.index = ["β0", "β1", "β2", "β3", "τ1", "τ2"]
pt.index.name = "Parameter"
c2 = pd.DataFrame({"NSS (this fit)": cmp_["NSS (this fit)"].map(pct), "Bootstrap": cmp_["Bootstrap"].map(pct),
                   "Fed GSW": cmp_["Fed GSW"].map(pct), "NSS − GSW": cmp_["NSS − GSW (bp)"].map(lambda x: f"{x:+.1f} bp"),
                   "Bootstrap − GSW": cmp_["Bootstrap − GSW (bp)"].map(lambda x: f"{x:+.1f} bp")})
c2.index.name = "Zero rate"
r.table(pt, caption="Table 2. Fitted Svensson parameters vs. the Fed's GSW parameters for the same date.")
r.table(c2, caption="Table 3. Continuously compounded zero rates on 30 September 2026.")
r.p(f"The independent fit lands very close to the Fed's: β1, β3 and τ2 are within a few percent of GSW's values and β0 sits "
    f"on its zero bound in both fits, a sign that β0 and β3 are only weakly identified when the curve is humped at the long "
    f"end. Fitted zero rates differ from GSW by {cmp_['NSS − GSW (bp)'].abs().min():.1f}–{cmp_['NSS − GSW (bp)'].abs().max():.1f} bp. "
    "The remaining gap reflects different inputs: GSW fits off-the-run coupon securities and excludes bills, while this fit "
    "uses the Treasury's on-the-run par curve including bills.")
r.image(F / "fig_curve.png", 15, "Figure 1. Par yields, bootstrapped zeros, the NSS fit and the Fed GSW curve.")
r.h1("4. Level, slope and curvature since 2006")
r.p(f"Each day I fit a three-factor Nelson-Siegel model to the par yields by ordinary least squares with the decay fixed at "
    f"Diebold and Li's (2006) value (0.0609 per month). Over {m['ns_days']:,} days the median fit error is "
    f"{m['ns_median_rmse_bp']:.1f} bp. The slope factor here is β1 (short minus long), so a negative value means an "
    f"upward-sloping curve.")
r.image(F / "fig_ns_factors.png", 15.5, "Figure 2. Daily Nelson-Siegel factors with NBER recessions shaded.")
lv = ns["Level"]
r.p(f"The level factor fell from about {lv.loc['2006'].mean() * 100:.1f}% in 2006 to a low of {lv.min() * 100:.1f}% in "
    f"{lv.idxmin():%B %Y} and has risen to {lv.iloc[-1] * 100:.1f}% by September 2026. The slope factor turned positive "
    f"(an inverted curve) in {ns.loc['2022':'2024', 'Slope'].gt(0).idxmax():%B %Y} during the Fed's hiking cycle, and "
    f"curvature swings most around policy turning points. Both recessions in the sample were preceded by an inverted curve "
    f"(slope above zero) within the previous 12 months: up to {ns.loc['2007','Slope'].max() * 100:.2f} points in 2007 and "
    f"{ns.loc['2019-03':'2020-02','Slope'].max() * 100:.2f} points in 2019, the classic inversion signal.")
r.h1("5. Principal components of daily yield changes")
r.p(f"Applied to {m['pca_days']:,} daily changes in the 1, 2, 3, 5, 7, 10, 20 and 30-year par yields, PCA finds the three "
    f"factors of Litterman and Scheinkman (1991): a level factor ({pct(ex[0],1)} of variance) with same-sign loadings at "
    f"every maturity, a slope factor ({pct(ex[1],1)}) that moves short and long yields in opposite directions, and a "
    f"curvature factor ({pct(ex[2],1)}) that moves the belly against the wings. Together they explain {pct(sum(ex[:3]),1)}.")
r.image(F / "fig_pca.png", 14, "Figure 3. Loadings of the first three principal components.")
r.h1("6. Three $100m portfolios")
p6 = pd.DataFrame({"Holdings (face, coupon)": port["Holdings"], "Modified duration": port["Modified duration"].map(lambda x: f"{x:.2f}"),
                   "Convexity": port["Convexity"].map(lambda x: f"{x:.1f}"),
                   "Avg. coupon": port["Average coupon / yield"].map(pct)})
p6.index.name = "Portfolio"
r.table(p6, caption="Table 4. Portfolios priced off the 30 September 2026 curve. All bonds are par bonds (coupon = par yield), "
        "so each portfolio is worth $100m today.", font=7.5)
r.p(f"The barbell holds {pct(1 - m['barbell_w30'],1)} in the 2-year and {pct(m['barbell_w30'],1)} in the 30-year so that its "
    f"modified duration equals the bullet's ({port.loc['Bullet','Modified duration']:.2f}). It has "
    f"{port.loc['Barbell','Convexity'] / port.loc['Bullet','Convexity']:.1f} times the bullet's convexity.")
r.h1("7. Six instant scenarios")
sd = pd.DataFrame({"Definition": [DESCR[k] for k in DESCR]}, index=list(DESCR))
sd.index.name = "Scenario"
r.table(sd, caption="Table 5. Scenarios, applied as shifts to continuously compounded zero rates.")
pv = pnl.pivot(index="Scenario", columns="Portfolio", values="Full revaluation ($m)").loc[list(DESCR)]
du = pnl.pivot(index="Scenario", columns="Portfolio", values="Duration only ($m)").loc[list(DESCR)]
dc = pnl.pivot(index="Scenario", columns="Portfolio", values="Duration + convexity ($m)").loc[list(DESCR)]
t6 = pd.DataFrame({f"{p}: full / dur / dur+cvx": [f"{a:+.2f} / {b:+.2f} / {c:+.2f}" for a, b, c in zip(pv[p], du[p], dc[p])]
                   for p in ["Bullet", "Barbell", "Ladder"]}, index=pv.index)
t6["Barbell − bullet"] = bb.iloc[:, 0].map(lambda x: f"{x:+.0f} bp")
t6.index.name = "Scenario"
r.table(t6, caption="Table 6. P&L in $m: full revaluation / duration-only / duration + convexity approximation. The approximations "
        "use each bond's modified duration and convexity and the scenario shift at the bond's maturity.", font=7.2)
r.image(F / "fig_scenarios.png", 15, "Figure 4. Full-revaluation P&L by scenario.")
r.p(f"<b>Parallel moves.</b> With equal durations, the barbell beats the bullet by about {bb.loc['Parallel +100bp'].iloc[0]:.0f} bp "
    f"whether rates rise or fall: that is its convexity. Duration alone misses this; adding convexity recovers most of it.")
r.p(f"<b>Curve reshaping dominates.</b> In the bull flattener the barbell's 30-year bond rallies and it gains "
    f"{bb.loc['Bull flattener'].iloc[0]:.0f} bp more than the bullet; in the bear steepener it loses "
    f"{-bb.loc['Bear steepener'].iloc[0]:.0f} bp more. The twist and the butterfly also favour the barbell, because its "
    f"risk sits in the wings while the bullet's sits in the belly.")
r.p("<b>When the approximations fail.</b> For non-parallel shifts, applying the shift at each bond's maturity to its yield "
    "is crude for a long bond whose early coupons sit at other maturities. In the bear steepener the approximation "
    f"overstates the barbell's loss ({du.loc['Bear steepener','Barbell']:+.2f} vs. {pv.loc['Bear steepener','Barbell']:+.2f} $m); "
    f"in the butterfly it shows zero for the barbell, because the shift is zero at 2 and 30 years, while full revaluation "
    f"shows {pv.loc['Butterfly','Barbell']:+.2f} $m, because the 30-year bond's coupons in the 5–10-year sector are hit. "
    "Key rate durations fix this.")
k2 = krd.copy().map(lambda x: f"{x:.2f}")
k2.index.name = "Portfolio"
r.table(k2, caption="Table 7. Key rate durations (triangular 1 bp bumps of the zero curve at 2, 5, 10 and 30 years). They sum "
        "to about (1 + y/2) times modified duration because they are defined on continuous zero rates.")
r.image(F / "fig_shifts_krd.png", 16, "Figure 5. Scenario shifts and key rate durations.")
r.h1("8. Twelve months of carry and roll-down")
h = pd.DataFrame({"Total": hor["Total"].map(pct), "Carry (yield unchanged)": hor["Carry"].map(pct),
                  "Roll-down": hor["Roll-down"].map(pct)})
h.index.name = "Portfolio"
r.table(h, caption="Table 8. 12-month return if the curve does not move. Carry holds each bond's yield constant; roll-down is the extra "
        "gain from bonds rolling down an upward-sloping curve. Coupons are not reinvested; the ladder's 1-year bond matures.")
r.p(f"The bullet earns the most: "
    f"{pct(hor.loc['Bullet','Total'])}, against {pct(hor.loc['Barbell','Total'])} for the barbell. The barbell gives up "
    f"{-m['carry_gap_bp']:.0f} bp a year: a lower coupon on the 2-year ({row['2 Yr']:.2f}%) and negative roll-down "
    f"on the 30-year, which sits on the inverted 20–30-year segment and loses value as it rolls towards the higher-yielding "
    f"20-year point. Convexity is not free.")
r.h1("Conclusion")
r.p(f"A bootstrapped curve reprices the market exactly, while an NSS fit gives a smooth curve close to the Fed's. Three "
    f"factors drive almost all yield changes, and for a bond portfolio the key choice is not duration but where on the "
    f"curve it sits. A duration-matched barbell is a bet on flattening and on volatility: it gained "
    f"{bb.loc['Bull flattener'].iloc[0]:.0f} bp over the bullet in a bull flattener and lost {-bb.loc['Bear steepener'].iloc[0]:.0f} bp "
    f"in a bear steepener, at a cost of {-m['carry_gap_bp']:.0f} bp of carry a year if nothing happens.")
r.h1("Limitations")
r.bullets(["Scenarios are instantaneous and ignore the carry earned while curves move.",
           "Par yields are indicative closing levels for on-the-run securities; no bid-ask, repo or liquidity premia.",
           "The daily Nelson-Siegel fit uses a fixed decay and par yields rather than zero rates, which is standard but approximate.",
           "Shifts are applied to zero rates; applying them to par yields would give slightly different numbers."])
r.h1("References")
r.bullets(["Diebold, F. and Li, C. (2006). Forecasting the Term Structure of Government Bond Yields. <i>Journal of Econometrics</i>, 130(2), 337–364.",
           "Gürkaynak, R., Sack, B. and Wright, J. (2007). The U.S. Treasury Yield Curve: 1961 to the Present. <i>Journal of Monetary Economics</i>, 54(8), 2291–2304.",
           "Litterman, R. and Scheinkman, J. (1991). Common Factors Affecting Bond Returns. <i>Journal of Fixed Income</i>, 1(1), 54–61.",
           "Nelson, C. and Siegel, A. (1987). Parsimonious Modeling of Yield Curves. <i>Journal of Business</i>, 60(4), 473–489.",
           "Svensson, L. (1994). Estimating and Interpreting Forward Interest Rates: Sweden 1992–1994. NBER Working Paper 4871."])
print("pages:", r.build())
