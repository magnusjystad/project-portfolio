# %% [markdown]
# # Project 7 — Factor premia since 1963, and do factor ETFs deliver them?
# Part A measures US equity factor returns July 1963 – August 2026 (the latest month in the
# Kenneth French Data Library at the time of writing). Part B regresses five iShares factor
# ETFs on the Fama-French five factors plus momentum.

# %%
import json
import sys
from pathlib import Path

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path[:0] = [str(ROOT), str(ROOT.parent)]

import numpy as np
import pandas as pd
from scipy import stats as st

from common import data as D
from common.plotting import PALETTE, setup, source
from src import factors as F

plt = setup()
DATA, FIG = ROOT / "data", ROOT / "report" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
pd.options.display.float_format = "{:.4f}".format
SRC_FF = "Source: Kenneth French Data Library (5 factors 2x3, momentum); author's calculations."

# %% [markdown]
# ## Data

# %%
ff = D.french("F-F_Research_Data_5_Factors_2x3", DATA / "ff5_monthly.csv")
mom = D.french("F-F_Momentum_Factor", DATA / "ff_momentum_monthly.csv")
fac = ff.join(mom, how="inner")
fac.columns = [c.strip() for c in fac.columns]
FACTORS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]
fac = fac.loc["1963-07":]
rec = D.fred("USREC", DATA / "fred_USREC.csv")["USREC"]
rec.index = rec.index + pd.offsets.MonthEnd(0)
cpi = D.fred("CPIAUCSL", DATA / "fred_CPIAUCSL.csv")["CPIAUCSL"]
cpi.index = cpi.index + pd.offsets.MonthEnd(0)
infl = cpi.pct_change(12, fill_method=None).rename("CPI YoY")
END = fac.index[-1]
print("Factors:", fac.index[0].date(), "to", END.date(), len(fac), "months")

# %% [markdown]
# ## A1. Premium, volatility, Sharpe, t-stat, drawdown, worst 5 years

# %%
A1 = pd.DataFrame({f: F.summary(fac[f]) for f in FACTORS}).T
A1

# %% [markdown]
# ## A2. Decade-by-decade annualized (compounded) returns

# %%
dec = (fac.index.year // 10) * 10
A2 = fac[FACTORS].groupby(dec).apply(lambda g: g.apply(F.ann_geo))
A2.index = [f"{d}s" + (" (from Jul 1963)" if d == 1960 else f" (to {END:%b %Y})" if d == 2020 else "")
            for d in A2.index]
A2

# %%
fig, ax = plt.subplots(figsize=(9, 4.2))
for f in FACTORS:
    r10 = fac[f].rolling(120).mean() * 12
    ax.plot(r10.index, r10, lw=1.4, label=f)
ax.axhline(0, color="grey", lw=0.8)
ax.set_title("Rolling 10-year average factor premium (annualized)")
ax.legend(ncol=6, fontsize=8.5)
source(ax, SRC_FF)
fig.savefig(FIG / "fig_rolling_10y_premia.png"); plt.show()

# %% [markdown]
# ## A3. Correlations: full sample and since 2010

# %%
C_full = fac[FACTORS].corr()
C_2010 = fac.loc["2010":, FACTORS].corr()
C_full.round(2), C_2010.round(2)

# %% [markdown]
# ## A4. Regimes: NBER recessions and inflation above 4%

# %%
# Each split uses every month with data for that split. FRED has no CPI for October 2025 (BLS did
# not publish it during the government shutdown), so that month is left out of the inflation split only.
reg_r = fac[FACTORS].join(rec).dropna()
reg_i = fac[FACTORS].join(infl).dropna()


def regime(col, mask_true, lab_true, lab_false):
    reg = reg_r if mask_true.name == "USREC" else reg_i
    a, b = reg.loc[mask_true, col], reg.loc[~mask_true, col]
    t = st.ttest_ind(a, b, equal_var=False)
    return {f"{lab_true} (avg/mo)": a.mean(), f"{lab_false} (avg/mo)": b.mean(),
            "Difference": a.mean() - b.mean(), "Welch t": t.statistic}


A4_rec = pd.DataFrame({f: regime(f, (reg_r["USREC"] == 1).rename("USREC"), "Recession", "Expansion") for f in FACTORS}).T
A4_inf = pd.DataFrame({f: regime(f, (reg_i["CPI YoY"] > 0.04).rename("CPI"), "CPI > 4%", "CPI <= 4%") for f in FACTORS}).T
n_rec, n_inf = int((reg_r["USREC"] == 1).sum()), int((reg_i["CPI YoY"] > 0.04).sum())
print(f"Recession months: {n_rec} of {len(reg_r)}; months with CPI YoY > 4%: {n_inf} of {len(reg_i)}")
A4_rec, A4_inf

# %% [markdown]
# ## A5. Value's lost decade: HML January 2007 – December 2020, and afterwards

# %%
h = fac["HML"]
lost = h.loc["2007-01":"2020-12"]
after = h.loc["2021-01":]
w_lost = (1 + lost).cumprod()
lost_cum, after_cum = w_lost.iloc[-1] - 1, (1 + after).prod() - 1
# Share of the lost-decade loss recovered: wealth path 1 -> (1+lost_cum) -> (1+lost_cum)(1+after_cum)
recovered = ((1 + lost_cum) * (1 + after_cum) - (1 + lost_cum)) / (1 - (1 + lost_cum))
trough = w_lost.idxmin()
A5 = {"HML cum. return Jan 2007 - Dec 2020": lost_cum,
      "HML ann. return Jan 2007 - Dec 2020": F.ann_geo(lost),
      "HML peak-to-trough in the period": F.max_drawdown(lost),
      "Trough month": str(trough.date()),
      f"HML cum. return Jan 2021 - {END:%b %Y}": after_cum,
      "Share of 2007-2020 loss recovered": recovered,
      "HML ann. return Jul 1963 - Dec 2006": F.ann_geo(h.loc[:"2006-12"])}
A5

# %%
fig, ax = plt.subplots(figsize=(9, 4))
wh = (1 + h.loc["2000":]).cumprod()
ax.plot(wh.index, wh, color=PALETTE[0], lw=1.6)
ax.axvspan(pd.Timestamp("2007-01-01"), pd.Timestamp("2020-12-31"), color="#C55A11", alpha=0.08,
           label="Jan 2007 - Dec 2020")
ax.set_yscale("log"); ax.set_title("HML (value) cumulative return since 2000, log scale")
ax.legend(loc="upper left")
source(ax, SRC_FF)
fig.savefig(FIG / "fig_value_lost_decade.png"); plt.show()

# %% [markdown]
# ## A6. Multi-factor blend: equal weight HML, RMW, CMA, Mom (monthly rebalanced)

# %%
blend = fac[["HML", "RMW", "CMA", "Mom"]].mean(axis=1).rename("Blend")
A6 = pd.DataFrame({c: {"Sharpe": F.summary(s)["Sharpe"], "Max drawdown": F.max_drawdown(s),
                       "Premium (ann.)": s.mean() * 12, "Volatility": s.std() * np.sqrt(12)}
                   for c, s in {**{f: fac[f] for f in ["HML", "RMW", "CMA", "Mom"]}, "Blend": blend}.items()}).T
A6

# %%
fig, ax = plt.subplots(figsize=(9, 4.4))
for f in FACTORS:
    w = (1 + fac[f]).cumprod()
    ax.plot(w.index, w, lw=1.3, label=f)
wb = (1 + blend).cumprod()
ax.plot(wb.index, wb, color="black", lw=2.2, label="Blend (HML, RMW, CMA, Mom)")
ax.set_yscale("log"); ax.set_title(f"Growth of $1 in each factor, Jul 1963 - {END:%b %Y} (log scale)")
ax.legend(ncol=4, fontsize=8)
source(ax, SRC_FF + " Long-short factors exclude the risk-free return.")
fig.savefig(FIG / "fig_cumulative_factors.png"); plt.show()

# %% [markdown]
# ## Part B. Do factor ETFs deliver their factor?

# %%
ETFS = {"MTUM": "Mom", "VLUE": "HML", "QUAL": "RMW", "SIZE": "SMB", "USMV": "Mkt-RF"}
px = D.prices(list(ETFS), "2013-07-01", "2026-10-01", DATA / "factor_etf_prices_daily.csv")
er = D.monthly_returns(px).loc["2013-08":"2026-09"]
er.to_csv(DATA / "factor_etf_monthly_returns.csv")
X = fac[FACTORS]
ex = er.sub(fac["RF"], axis=0).dropna()   # French RF; sample ends with the factor data
print("Regression sample:", ex.index[0].date(), "to", ex.index[-1].date(), len(ex), "months")

rows, models = {}, {}
for etf, target in ETFS.items():
    m = F.regress(ex[etf], X)
    models[etf] = m
    row = {"Alpha (ann.)": m.params["const"] * 12, "t(alpha)": m.tvalues["const"]}
    for f in FACTORS:
        row[f] = m.params[f]
        row[f"t({f})"] = m.tvalues[f]
    row["R2"] = m.rsquared
    rows[etf] = row
B2 = pd.DataFrame(rows).T
B2

# %% [markdown]
# ## Robustness: CAPM and Fama-French 3-factor alphas

# %%
rob = {}
for etf in ETFS:
    for name, cols in {"CAPM": ["Mkt-RF"], "FF3": ["Mkt-RF", "SMB", "HML"]}.items():
        mm = F.regress(ex[etf], X[cols])
        rob[(etf, name)] = {"Alpha (ann.)": mm.params["const"] * 12, "t(alpha)": mm.tvalues["const"],
                            "Beta": mm.params["Mkt-RF"], "R2": mm.rsquared}
B_rob = pd.DataFrame(rob).T
B_rob.to_csv(DATA / "B_robust_capm_ff3.csv")
B_rob

# %% [markdown]
# ## B3. Is the biggest loading the target factor?
# For MTUM, VLUE, QUAL and SIZE, "biggest" means the largest loading among the five style
# factors (SMB, HML, RMW, CMA, Mom), since every long-only equity fund has a market beta near 1.
# For USMV the target is a low market beta: we test beta < 1.

# %%
STYLE = ["SMB", "HML", "RMW", "CMA", "Mom"]
B3 = {}
for etf, target in ETFS.items():
    m = models[etf]
    if etf == "USMV":
        b = m.params["Mkt-RF"]
        t_lt1 = (b - 1) / m.bse["Mkt-RF"]
        B3[etf] = {"Target": "Mkt-RF < 1", "Target loading": b, "t-stat": t_lt1,
                   "Largest style loading": max(STYLE, key=lambda f: abs(m.params[f])),
                   "Delivers target?": bool(b < 1 and t_lt1 < -2)}
    else:
        biggest = max(STYLE, key=lambda f: m.params[f])
        B3[etf] = {"Target": target, "Target loading": m.params[target], "t-stat": m.tvalues[target],
                   "Largest style loading": biggest,
                   "Delivers target?": bool(biggest == target and m.tvalues[target] > 2)}
B3 = pd.DataFrame(B3).T
B3

# %%
# Headline chart: table of loadings with t-stats as a heatmap
L = B2[FACTORS].astype(float)
T = B2[[f"t({f})" for f in FACTORS]].astype(float).values
fig, ax = plt.subplots(figsize=(8.6, 3.6))
im = ax.imshow(L.values, cmap="RdBu", vmin=-1.2, vmax=1.2, aspect="auto")
ax.set_xticks(range(len(FACTORS)), FACTORS); ax.set_yticks(range(len(L)), [f"{e} (target: {'low beta' if e == 'USMV' else ETFS[e]})" for e in L.index])
ax.grid(False)
for i in range(L.shape[0]):
    for j in range(L.shape[1]):
        tgt = (FACTORS[j] == ETFS[L.index[i]])
        ax.text(j, i, f"{L.values[i, j]:.2f}\n(t={T[i, j]:.1f})", ha="center", va="center", fontsize=8,
                fontweight="bold" if tgt else "normal",
                color="white" if abs(L.values[i, j]) > 0.75 else "black")
        if tgt:
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec="black", lw=2))
ax.set_title(f"Factor loadings of iShares factor ETFs, {ex.index[0]:%b %Y} - {ex.index[-1]:%b %Y}")
source(ax, "Source: yfinance, Kenneth French Data Library; Newey-West t-stats (3 lags). Boxed = target factor.")
fig.savefig(FIG / "fig_etf_loadings.png"); plt.show()

# %% [markdown]
# ## B4. Rolling 36-month loading on the target factor

# %%
roll = {etf: F.rolling_beta(ex[etf], X, tgt, 36) for etf, tgt in ETFS.items()}
fig, ax = plt.subplots(figsize=(9, 4.2))
for etf, s in roll.items():
    ax.plot(s.index, s, lw=1.6, label=f"{etf} on {'Mkt-RF' if etf == 'USMV' else ETFS[etf]}")
ax.axhline(0, color="grey", lw=0.8); ax.axhline(1, color="grey", lw=0.6, ls=":")
ax.set_title("Rolling 36-month loading on each ETF's target factor")
ax.legend(ncol=3, fontsize=8.5)
source(ax, "Source: yfinance, Kenneth French Data Library; author's calculations. 6-factor regressions.")
fig.savefig(FIG / "fig_rolling_target_loading.png"); plt.show()
pd.DataFrame(roll).to_csv(DATA / "rolling_target_loadings.csv")

# %% [markdown]
# ## ETF summary statistics (context)

# %%
etf_stats = pd.DataFrame({e: {"Ann. return": F.ann_geo(er[e].loc[:ex.index[-1]]),
                              "Volatility": er[e].loc[:ex.index[-1]].std() * np.sqrt(12),
                              "Sharpe": ex[e].mean() / ex[e].std() * np.sqrt(12)} for e in ETFS}).T
mkt = fac.loc[ex.index, "Mkt-RF"]
etf_stats.loc["Market (Mkt-RF + RF)"] = [F.ann_geo(mkt + fac.loc[ex.index, "RF"]),
                                        mkt.std() * np.sqrt(12), mkt.mean() / mkt.std() * np.sqrt(12)]
etf_stats

# %% [markdown]
# ## Save

# %%
A1.to_csv(DATA / "A1_factor_summary.csv"); A2.to_csv(DATA / "A2_decades.csv")
C_full.to_csv(DATA / "A3_corr_full.csv"); C_2010.to_csv(DATA / "A3_corr_since2010.csv")
A4_rec.to_csv(DATA / "A4_recession.csv"); A4_inf.to_csv(DATA / "A4_inflation.csv")
A6.to_csv(DATA / "A6_blend.csv"); B2.to_csv(DATA / "B2_regressions.csv"); B3.to_csv(DATA / "B3_target_check.csv")
etf_stats.to_csv(DATA / "B_etf_stats.csv")
json.dump({"factor_start": str(fac.index[0].date()), "factor_end": str(END.date()), "n_factor": len(fac),
           "reg_start": str(ex.index[0].date()), "reg_end": str(ex.index[-1].date()), "n_reg": len(ex),
           "n_recession": n_rec, "n_infl": n_inf, "n_rec_sample": len(reg_r), "n_infl_sample": len(reg_i),
           "A5": {k: (float(v) if not isinstance(v, str) else v) for k, v in A5.items()}},
          open(DATA / "meta.json", "w"), indent=2)
