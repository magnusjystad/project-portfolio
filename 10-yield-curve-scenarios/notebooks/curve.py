# %% [markdown]
# # Project 11 — US Treasury yield curve model and bond portfolio scenario tool
# Curve date: 30 September 2026. Data: U.S. Treasury Daily Par Yield Curve Rates (2006–2026),
# Federal Reserve Gürkaynak-Sack-Wright (GSW) zero curve, NBER recessions (FRED USREC).

# %%
import json
import sys
from pathlib import Path

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path[:0] = [str(ROOT), str(ROOT.parent)]

import numpy as np
import pandas as pd

from common import data as D
from common.plotting import PALETTE, setup, source
from yieldcurve import bonds as B, curve as C, scenarios as S

plt = setup()
DATA, FIG = ROOT / "data", ROOT / "report" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
DATE = pd.Timestamp("2026-09-30")
SRC_T = "Source: U.S. Treasury Daily Par Yield Curve Rates; author's calculations."
par_all = pd.read_csv(DATA / "treasury_par_yields_daily.csv", index_col=0, parse_dates=True).loc["2006":"2026-09-30"]
gsw = pd.read_csv(DATA / "gsw_zero_curve_2006_2026.csv", index_col=0, parse_dates=True)
rec = D.fred("USREC", DATA / "fred_USREC.csv")["USREC"]
print(par_all.index[0].date(), "to", par_all.index[-1].date(), len(par_all), "days")

# %% [markdown]
# ## 1. Bootstrap the zero curve on 30 September 2026

# %%
par = C.par_points(par_all.loc[DATE])
zc = C.ZeroCurve(par)
grid = zc.grid
boot = pd.DataFrame({"Par (spline)": zc.par_grid, "Discount factor": zc.df_grid,
                     "Zero (semiannual)": zc.zero_sa(grid), "Zero (continuous)": zc.zero_cc(grid)}, index=grid)
boot.index.name = "Maturity (years)"
check = max(abs(zc.par_yield(T) - zc.spline(T)) for T in grid)
print(f"Max repricing error of par bonds on the grid: {check * 1e4:.2e} bp")
boot.loc[[0.5, 1, 2, 3, 5, 7, 10, 20, 30]]

# %% [markdown]
# ## 2. Nelson-Siegel-Svensson by nonlinear least squares; comparison with the Fed (GSW) curve

# %%
nss_p, nss_rmse = C.fit_nss(par)
g = gsw.loc[DATE]
cmp_rows = {}
for T in (2, 5, 10, 30):
    mine = float(C.nss_zero(np.array([T]), *nss_p)[0])
    boot_z = float(zc.zero_cc(T))
    fed = g[f"SVENY{T:02d}"] / 100
    cmp_rows[f"{T}y"] = {"NSS (this fit)": mine, "Bootstrap": boot_z, "Fed GSW": fed,
                         "NSS − GSW (bp)": (mine - fed) * 1e4, "Bootstrap − GSW (bp)": (boot_z - fed) * 1e4}
CMP = pd.DataFrame(cmp_rows).T
NSSP = pd.Series(nss_p, ["beta0", "beta1", "beta2", "beta3", "tau1", "tau2"])
GSWP = pd.Series([g["BETA0"] / 100, g["BETA1"] / 100, g["BETA2"] / 100, g["BETA3"] / 100, g["TAU1"], g["TAU2"]], NSSP.index)
print(f"NSS fit RMSE on par yields: {nss_rmse * 1e4:.2f} bp")
pd.DataFrame({"This fit": NSSP, "Fed GSW": GSWP}), CMP

# %%
fig, ax = plt.subplots(figsize=(8.6, 4.2))
tt = np.linspace(0.25, 30, 300)
ax.plot(tt, C.nss_zero(tt, *nss_p) * 100, color=PALETTE[0], lw=2, label="NSS zero curve (this fit)")
ax.plot(grid, zc.zero_cc(grid) * 100, "o", ms=3, color=PALETTE[1], label="Bootstrapped zeros (continuous)")
ax.plot(range(1, 31), [g[f"SVENY{i:02d}"] for i in range(1, 31)], "--", color=PALETTE[2], lw=1.4, label="Fed GSW zero curve")
ax.plot(par.index, par.values * 100, "s", ms=4, color="black", label="Treasury par yields")
ax.set_xlabel("Maturity (years)"); ax.set_ylabel("%"); ax.legend(fontsize=8)
ax.set_title("US Treasury curve, 30 September 2026")
source(ax, SRC_T + " Federal Reserve GSW (feds200628).")
fig.savefig(FIG / "fig_curve.png"); plt.show()

# %% [markdown]
# ## 3. Daily Nelson-Siegel fit 2006–2026: level, slope, curvature

# %%
STD = ["1 Mo", "3 Mo", "6 Mo", "1 Yr", "2 Yr", "3 Yr", "5 Yr", "7 Yr", "10 Yr", "20 Yr", "30 Yr"]
ns_rows, ns_rmse = {}, {}
for d, row in par_all[STD].iterrows():
    p = C.par_points(row)
    if len(p) < 6:
        continue
    b = C.fit_ns_ols(p)
    ns_rows[d] = b
    ns_rmse[d] = np.sqrt(np.mean((C.ns_loadings(p.index.values, 1 / 0.7308) @ b - p.values) ** 2))
NS = pd.DataFrame(ns_rows, index=["Level", "Slope", "Curvature"]).T
NS["RMSE (bp)"] = pd.Series(ns_rmse) * 1e4
print(f"{len(NS)} daily fits; median RMSE {NS['RMSE (bp)'].median():.1f} bp, 95th pct {NS['RMSE (bp)'].quantile(.95):.1f} bp")
NS.describe().T

# %%
fig, ax = plt.subplots(figsize=(10, 4.3))
r = rec.loc["2006":"2026-09"]
for start, grp in r[r == 1].groupby((r != 1).cumsum()):
    ax.axvspan(grp.index[0], grp.index[-1] + pd.offsets.MonthEnd(0), color="grey", alpha=0.18, lw=0)
for i, c in enumerate(["Level", "Slope", "Curvature"]):
    ax.plot(NS.index, NS[c] * 100, lw=1.2, color=PALETTE[i], label=c)
ax.axhline(0, color="black", lw=0.6)
ax.set_ylabel("%"); ax.legend(ncol=3, fontsize=8.5)
ax.set_title("Daily Nelson-Siegel factors, 2006–2026 (grey: NBER recessions)")
source(ax, SRC_T + " NBER via FRED USREC. Diebold-Li fixed decay (0.0609/month).")
fig.savefig(FIG / "fig_ns_factors.png"); plt.show()

# %% [markdown]
# ## 4. PCA on daily yield changes (1, 2, 3, 5, 7, 10, 20, 30y)

# %%
PCA_T = ["1 Yr", "2 Yr", "3 Yr", "5 Yr", "7 Yr", "10 Yr", "20 Yr", "30 Yr"]
dY = par_all[PCA_T].diff().dropna() * 100   # basis points
cov = np.cov(dY.values.T)
ev, evec = np.linalg.eigh(cov)
order = ev.argsort()[::-1]
ev, evec = ev[order], evec[:, order]
evec = evec * np.sign(evec.sum(axis=0))  # level loads positively
evec[:, 1] *= np.sign(evec[-1, 1] - evec[0, 1])  # slope: long end up
expl = ev / ev.sum()
PCA = pd.DataFrame(evec[:, :3], index=PCA_T, columns=["PC1 (level)", "PC2 (slope)", "PC3 (curvature)"])
print("Variance explained:", np.round(expl[:5], 4), "cumulative 3:", round(expl[:3].sum(), 4), "| days:", len(dY))
PCA

# %%
fig, ax = plt.subplots(figsize=(8.6, 3.8))
mats = [1, 2, 3, 5, 7, 10, 20, 30]
for i, c in enumerate(PCA.columns):
    ax.plot(mats, PCA[c], "o-", color=PALETTE[i], label=f"{c}: {expl[i]:.1%} of variance")
ax.axhline(0, color="black", lw=0.6); ax.set_xlabel("Maturity (years)"); ax.set_ylabel("Loading")
ax.set_title(f"Principal components of daily par yield changes, {dY.index[0]:%b %Y} – {dY.index[-1]:%b %Y}")
ax.legend(fontsize=8)
source(ax, SRC_T)
fig.savefig(FIG / "fig_pca.png"); plt.show()

# %% [markdown]
# ## 5. Three $100m portfolios priced off the 30 September 2026 curve

# %%
bullet_b = B.par_bond(zc, 7)
b2, b30 = B.par_bond(zc, 2), B.par_bond(zc, 30)
D7 = bullet_b.mod_duration_convexity(bullet_b.coupon)[0]
D2 = b2.mod_duration_convexity(b2.coupon)[0]
D30 = b30.mod_duration_convexity(b30.coupon)[0]
w30 = (D7 - D2) / (D30 - D2)              # par bonds: market value = face, so weights are by face
NOT = 100e6
PORTS = {"Bullet": B.Portfolio([bullet_b], [NOT]),
         "Barbell": B.Portfolio([b2, b30], [NOT * (1 - w30), NOT * w30]),
         "Ladder": B.Portfolio([B.par_bond(zc, k) for k in range(1, 11)], [NOT / 10] * 10)}
desc = {}
for k, pt in PORTS.items():
    conv = sum(n / pt.value(zc) * b.mod_duration_convexity(b.coupon)[1] * b.price(zc) / b.face for b, n in zip(pt.bonds, pt.notionals))
    y = sum(n * b.coupon for b, n in zip(pt.bonds, pt.notionals)) / pt.notionals.sum()
    desc[k] = {"Value ($m)": pt.value(zc) / 1e6, "Modified duration": pt.mod_duration(zc), "Convexity": conv,
               "Average coupon / yield": y,
               "Holdings": ", ".join(f"{b.maturity:g}y {n / 1e6:.1f}m @ {b.coupon:.3%}" for b, n in zip(pt.bonds, pt.notionals))}
PDESC = pd.DataFrame(desc).T
PDESC

# %% [markdown]
# ## 6–7. Six instant scenarios: full revaluation vs. duration vs. duration + convexity; key rate durations

# %%
rows = []
for sc, fn in S.SCENARIOS.items():
    for k, pt in PORTS.items():
        res = S.portfolio_pnl(pt, zc, fn)
        rows.append({"Scenario": sc, "Portfolio": k, **{f"{m} ($m)": v / 1e6 for m, v in res.items()},
                     "Full revaluation (bp of value)": res["Full revaluation"] / pt.value(zc) * 1e4})
PNL = pd.DataFrame(rows)
KRD = pd.DataFrame({k: S.key_rate_durations(pt, zc) for k, pt in PORTS.items()}).T
KRD["Sum of KRDs"] = KRD.sum(axis=1)
KRD["Modified duration"] = PDESC["Modified duration"]
PNL.pivot(index="Scenario", columns="Portfolio", values="Full revaluation (bp of value)").loc[list(S.SCENARIOS)], KRD

# %%
piv = PNL.pivot(index="Scenario", columns="Portfolio", values="Full revaluation (bp of value)").loc[list(S.SCENARIOS)]
fig, ax = plt.subplots(figsize=(9.5, 4.2))
x = np.arange(len(piv))
for i, k in enumerate(["Bullet", "Barbell", "Ladder"]):
    ax.bar(x + (i - 1) * 0.27, piv[k] / 100, 0.27, label=k, color=PALETTE[i])
ax.axhline(0, color="black", lw=0.6)
ax.set_xticks(x, piv.index, fontsize=8.5); ax.set_ylabel("P&L, % of value")
ax.set_title("Instant scenario P&L by full revaluation"); ax.legend()
source(ax, SRC_T)
fig.savefig(FIG / "fig_scenarios.png"); plt.show()

# %%
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
for i, (sc, fn) in enumerate(S.SCENARIOS.items()):
    axes[0].plot(np.linspace(0, 30, 61), fn(np.linspace(0, 30, 61)) * 1e4, lw=1.6, color=PALETTE[i], label=sc)
axes[0].set_title("Scenario shifts (bp)"); axes[0].set_xlabel("Maturity (years)"); axes[0].legend(fontsize=7.5)
KRD[[c for c in KRD.columns if c.startswith("KRD")]].T.plot.bar(ax=axes[1], color=PALETTE[:3], rot=0)
axes[1].set_title("Key rate durations"); axes[1].legend(fontsize=8)
fig.savefig(FIG / "fig_shifts_krd.png"); plt.show()

# %% [markdown]
# ## 8. 12-month horizon return with the curve unchanged: carry + roll-down

# %%
HOR = pd.DataFrame({k: S.horizon_return(pt, zc) for k, pt in PORTS.items()}).T
HOR

# %% [markdown]
# ## Headline comparison: duration-matched barbell vs. bullet

# %%
diff = (piv["Barbell"] - piv["Bullet"]).rename("Barbell − bullet (bp)")
carry_gap = (HOR.loc["Barbell", "Total"] - HOR.loc["Bullet", "Total"]) * 1e4
best_sc = diff.idxmax()
print(f"Barbell beats bullet most in '{best_sc}': {diff.max():.0f} bp; 12-month carry+roll gap: {carry_gap:.0f} bp")
diff

# %% [markdown]
# ## Save

# %%
boot.to_csv(DATA / "bootstrap_2026-09-30.csv"); CMP.to_csv(DATA / "nss_vs_gsw.csv")
pd.DataFrame({"This fit": NSSP, "Fed GSW": GSWP}).to_csv(DATA / "nss_parameters.csv")
NS.to_csv(DATA / "ns_daily_factors.csv"); PCA.to_csv(DATA / "pca_loadings.csv")
PDESC.to_csv(DATA / "portfolios.csv"); PNL.to_csv(DATA / "scenario_pnl.csv", index=False)
KRD.to_csv(DATA / "key_rate_durations.csv"); HOR.to_csv(DATA / "horizon_returns.csv"); diff.to_csv(DATA / "barbell_minus_bullet.csv")
json.dump({"date": str(DATE.date()), "nss_rmse_bp": nss_rmse * 1e4, "pca_explained": expl[:5].tolist(), "pca_days": len(dY),
           "ns_days": len(NS), "ns_median_rmse_bp": float(NS["RMSE (bp)"].median()), "barbell_w30": w30,
           "best_scenario": best_sc, "best_gain_bp": float(diff.max()), "carry_gap_bp": float(carry_gap),
           "max_boot_error_bp": float(check * 1e4)}, open(DATA / "meta.json", "w"), indent=2)
