"""Brinson-Fachler attribution and Carino linking."""
import numpy as np
import pandas as pd


def brinson_fachler(wp: pd.Series, rp: pd.Series, wb: pd.Series, rb: pd.Series) -> pd.DataFrame:
    """Sector-level allocation, selection and interaction. Weights sum to 1 in each portfolio; sector
    returns rp/rb are the weighted returns inside each sector (NaN where the portfolio holds nothing)."""
    idx = wp.index.union(wb.index)
    wp, wb = wp.reindex(idx).fillna(0), wb.reindex(idx).fillna(0)
    Rb = float((wb * rb.reindex(idx).fillna(0)).sum())
    rb_ = rb.reindex(idx)
    rp_ = rp.reindex(idx)
    # Where the benchmark holds nothing, the benchmark sector return is undefined: allocation uses the
    # total benchmark return (so allocation = 0) and the whole effect is selection+interaction.
    rb_eff = rb_.fillna(Rb)
    rp_eff = rp_.fillna(rb_eff)
    alloc = (wp - wb) * (rb_eff - Rb)
    sel = wb * (rp_eff - rb_eff)
    inter = (wp - wb) * (rp_eff - rb_eff)
    return pd.DataFrame({"Fund weight": wp, "Bench weight": wb, "Fund return": rp_, "Bench return": rb_,
                         "Allocation": alloc, "Selection": sel, "Interaction": inter})


def carino(effects: dict, Rp: pd.Series, Rb: pd.Series) -> pd.DataFrame:
    """Link per-period effects (dict period -> DataFrame of effects) with Carino (1999) smoothing."""
    def k(rp, rb):
        return (np.log1p(rp) - np.log1p(rb)) / (rp - rb) if abs(rp - rb) > 1e-12 else 1 / (1 + rp)
    RP, RB = float(np.prod(1 + Rp) - 1), float(np.prod(1 + Rb) - 1)
    K = k(RP, RB)
    out = None
    for t, e in effects.items():
        part = e * (k(Rp[t], Rb[t]) / K)
        out = part if out is None else out.add(part, fill_value=0)
    return out
