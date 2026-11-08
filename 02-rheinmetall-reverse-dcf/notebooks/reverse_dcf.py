# %% [markdown]
# # Project 2 — Reverse DCF: is Rheinmetall priced for perfection?
# Runs `src/model.py` (reproduced with formulas in `model/rheinmetall_reverse_dcf.xlsx`, checked by `src/check_workbook.py`)
# and draws the charts used in the memo.

# %%
import json
import sys
from pathlib import Path

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path[:0] = [str(ROOT), str(ROOT.parent)]

import numpy as np
import pandas as pd

from common.plotting import PALETTE, setup, source
from src import model as M
from src import peers as PE

plt = setup()
DATA, FIG = ROOT / "data", ROOT / "report" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
R = M.run()
mk = R["mk"]
pd.Series(mk).round(4)

# %%
print(f"(a) implied CAGR {R['a_cagr']:.2%} -> 2035 sales EUR {R['a_sales_2035']:,.0f}m; (b) implied margin {R['b_margin']:.2%}")
print({n: round(v["per_share"], 0) for n, v in R["case_val"].items()}, "WACC that equates each case to the price:",
      {n: round(v, 4) for n, v in R["implied_wacc"].items()})
R["wacc_sens"].round(3)

# %%
H = M.history()
H.loc["Book-to-bill"] = H.loc["Rheinmetall Nomination"] / H.loc["Sales"]
H.loc["Operating margin"] = H.loc["Operating result"] / H.loc["Sales"]
H.round(3)

# %%
PM = PE.margins()
PEERSTAT = pd.DataFrame({"5-yr average 2021–25": PM[[2021, 2022, 2023, 2024, 2025]].mean(axis=1),
                         "Best year 2021–25": PM[[2021, 2022, 2023, 2024, 2025]].max(axis=1),
                         "Consensus 2028": PM[2028]})
PEERSTAT.round(3)

# %% [markdown]
# ## Charts

# %%
g = R["grid"]
fig, ax = plt.subplots(figsize=(8.6, 4.6))
im = ax.imshow(g.values, cmap="RdYlGn", aspect="auto", origin="lower",
               norm=__import__("matplotlib").colors.TwoSlopeNorm(vcenter=mk["price"], vmin=g.values.min(), vmax=g.values.max()))
ax.set_xticks(range(len(g.columns)), [f"{c:.0%}" for c in g.columns]); ax.set_yticks(range(len(g.index)), [f"{c:.1%}" for c in g.index])
for i in range(g.shape[0]):
    for j in range(g.shape[1]):
        v = g.values[i, j]
        ax.text(j, i, f"{v:,.0f}", ha="center", va="center", fontsize=6.5, fontweight="bold" if abs(v / mk["price"] - 1) <= 0.1 else "normal")
cs = ax.contour(g.values, levels=[mk["price"]], colors="black", linewidths=1.6)
ax.set_xlabel("Operating margin from 2030"); ax.set_ylabel("Sales CAGR 2025–2035")
ax.set_title(f"Value per share (€) — black line = share price €{mk['price']:,.0f}; WACC {mk['wacc']:.1%}")
ax.grid(False)
source(ax, "Source: author's reverse DCF; Rheinmetall reports; yfinance; Bundesbank; Damodaran.")
fig.savefig(FIG / "fig_grid.png"); plt.show()

# %%
tot = R["budget"]
fig, ax = plt.subplots(figsize=(8.6, 3.9))
years = list(range(2025, 2036))
imp = pd.Series({y: M.SALES_2025 * (1 + R["a_cagr"]) ** (y - 2025) for y in years}) * M.EUR_SALES_SHARE_2025
ax.plot(years, imp / tot[years] * 100, color="#B22222", lw=2.2, ls="--", label=f"Implied by the share price ({R['a_cagr']:.1%} sales CAGR, 20% margin)")
for i, n in enumerate(["Bear", "Base", "Bull"]):
    s_ = pd.concat([pd.Series({2025: M.SALES_2025}), R["cases"][n][0]]) * M.EUR_SALES_SHARE_2025
    ax.plot(s_.index, s_ / tot[s_.index] * 100, color=PALETTE[i], lw=1.6, label=f"{n} case")
ax.axhline(R["tests"]["budget"]["today"] * 100, color="grey", lw=0.8, ls=":")
ax.text(2025.1, R["tests"]["budget"]["today"] * 100 + 0.3, f"2025 actual: {R['tests']['budget']['today']:.1%}", fontsize=7.5, color="grey")
ax.set_ylabel("% of European NATO equipment spending"); ax.legend(fontsize=7.5, loc="upper left")
ax.set_title(f"Rheinmetall's European sales as a share of European NATO equipment spending\n(spending €{tot[2025] / 1000:,.0f}bn in 2025 → €{tot[2035] / 1000:,.0f}bn in 2035 on the Hague 3.5%-of-GDP path)", fontsize=10)
source(ax, "Source: NATO Defence Expenditure 2014–2026 (July 2026, Tables 2, 3, 8a); IMF WEO GDP; Rheinmetall AR 2025; author's calculations.")
fig.savefig(FIG / "fig_budget.png"); plt.show()

# %%
fig, ax = plt.subplots(figsize=(8.6, 3.8))
order = ["Leonardo", "Saab", "BAE Systems", "Thales", "Kongsberg Gruppen", "Rheinmetall"]
x = np.arange(len(order))
ax.bar(x - 0.2, PEERSTAT.loc[order, "5-yr average 2021–25"] * 100, 0.4, color=PALETTE[0], label="EBIT margin, 5-yr average 2021–25")
ax.bar(x + 0.2, PEERSTAT.loc[order, "Best year 2021–25"] * 100, 0.4, color=PALETTE[1], label="Best year 2021–25")
for val, lab, c in [(R["b_margin"], "Implied by price at management's sales path", "#B22222"), (0.185, "Our base case", "black"),
                    (0.21, "Our bull case (management: >20%)", "#2E8B57")]:
    ax.axhline(val * 100, color=c, ls="--", lw=1.2)
    ax.text(-0.45, val * 100 + 0.35, f"{lab}: {val:.1%}", fontsize=7.5, color=c, ha="left", bbox=dict(fc="white", ec="none", pad=0.5))
ax.set_xticks(x, order, fontsize=8); ax.set_ylabel("%"); ax.set_ylim(0, 27); ax.legend(fontsize=7.5, loc="upper right", ncol=2)
ax.set_title("Margin test: implied margin vs. peers and our cases")
source(ax, "Source: MarketScreener (EBIT / net sales, 7 Oct 2026); author's reverse DCF.")
fig.savefig(FIG / "fig_margins.png"); plt.show()

# %%
fig, ax = plt.subplots(figsize=(8.6, 3.6))
yrs = [2022, 2023, 2024, 2025]
ax.bar(np.array(yrs) - 0.2, H.loc["Sales", yrs] / 1000, 0.4, color=PALETTE[0], label="Sales")
ax.bar(np.array(yrs) + 0.2, H.loc["Rheinmetall Nomination", yrs] / 1000, 0.4, color=PALETTE[1], label="Rheinmetall Nomination (order inflow)")
ax2 = ax.twinx(); ax2.plot(yrs, H.loc["Rheinmetall Backlog", yrs] / 1000, color="black", marker="o", label="Rheinmetall Backlog (rhs)"); ax2.grid(False)
ax2.plot([2026.5], [80.467], "ko", mfc="white"); ax2.annotate("H1 2026: €80.5bn", (2026.5, 80.467), xytext=(-60, 5), textcoords="offset points", fontsize=8)
ax.set_ylabel("€bn"); ax2.set_ylabel("Backlog, €bn"); ax.set_xticks(yrs + [2026.5], [str(y) for y in yrs] + ["H1 26"])
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, fontsize=7.5, loc="upper left")
ax.set_title("Orders are running far ahead of sales")
source(ax, "Source: Rheinmetall annual report 2025 and H1 2026 report (continuing operations).")
fig.savefig(FIG / "fig_backlog.png"); plt.show()

# %% [markdown]
# ## Save

# %%
R["grid"].to_csv(DATA / "out_grid.csv"); R["wacc_sens"].to_csv(DATA / "out_wacc_sensitivity.csv")
pd.DataFrame({n: pd.concat([R["cases"][n][0].rename("Sales"), R["cases"][n][1].rename("Margin")], axis=1).stack() for n in R["cases"]}).to_csv(DATA / "out_cases.csv")
R["budget"].to_csv(DATA / "out_budget_eur.csv"); R["nato_check"].to_csv(DATA / "out_nato_ocr_check.csv"); PEERSTAT.to_csv(DATA / "out_peer_margins.csv")
json.dump({"mk": mk, "k": R["k"], "fx": R["fx"], "a_cagr": R["a_cagr"], "a_sales_2035": R["a_sales_2035"], "b_margin": R["b_margin"],
           "case_value": {n: v["per_share"] for n, v in R["case_val"].items()}, "case_ev": {n: v["ev"] for n, v in R["case_val"].items()},
           "implied_wacc": R["implied_wacc"], "tests": R["tests"]}, open(DATA / "out_results.json", "w"), indent=2, default=float)
