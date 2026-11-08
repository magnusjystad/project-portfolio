"""Curve scenarios, P&L attribution, key rate durations and carry/roll-down."""
from __future__ import annotations

import numpy as np
import pandas as pd

KEYS = [2, 5, 10, 30]


def _interp(points):
    """Shift function linear between (maturity, bp) points and flat outside them."""
    x, y = zip(*sorted(points.items()))
    return lambda t: np.interp(np.asarray(t, float), x, np.array(y) / 1e4)


SCENARIOS = {
    "Parallel +100bp": _interp({2: 100, 30: 100}),
    "Parallel -100bp": _interp({2: -100, 30: -100}),
    "Bear steepener": _interp({2: 0, 30: 100}),
    "Bull flattener": _interp({2: 0, 30: -100}),
    "Twist": _interp({2: 50, 30: -50}),
    "Butterfly": _interp({2: 0, 5: 50, 10: 50, 30: 0}),
}
DESCR = {
    "Parallel +100bp": "+100 bp at all maturities",
    "Parallel -100bp": "−100 bp at all maturities",
    "Bear steepener": "2y unchanged, 30y +100 bp, linear in between; flat outside",
    "Bull flattener": "2y unchanged, 30y −100 bp, linear in between; flat outside",
    "Twist": "2y +50 bp, 30y −50 bp, linear in between; flat outside",
    "Butterfly": "5y–10y +50 bp; 2y and 30y unchanged; linear between 2–5y and 10–30y",
}


def bond_pnl(bond, notional, curve, shift_fn):
    """Full revaluation vs. duration-only vs. duration+convexity, using each bond's own yield change
    (the shift at its maturity, applied to its yield to maturity)."""
    p0 = bond.price(curve)
    y0 = bond.ytm(p0)
    full = bond.price(curve.shifted(shift_fn)) - p0
    dy = float(shift_fn(np.array([bond.maturity]))[0])
    D, C = bond.mod_duration_convexity(y0)
    dur = -D * dy * p0
    dc = dur + 0.5 * C * dy ** 2 * p0
    k = notional / bond.face
    return k * full, k * dur, k * dc


def portfolio_pnl(port, curve, shift_fn):
    out = np.zeros(3)
    for b, n in zip(port.bonds, port.notionals):
        out += np.array(bond_pnl(b, n, curve, shift_fn))
    return dict(zip(["Full revaluation", "Duration only", "Duration + convexity"], out))


def key_rate_shift(key, bp=1.0, keys=KEYS):
    """Triangular bump of `bp` at a key maturity, zero at neighbouring keys; flat beyond the end keys."""
    pts = {k: 0.0 for k in keys}
    pts[key] = bp
    i = keys.index(key)
    x = [0.0] + list(keys) + [100.0]
    y = [pts[keys[0]] if i == 0 else 0.0] + [pts[k] for k in keys] + [pts[keys[-1]] if i == len(keys) - 1 else 0.0]
    return lambda t: np.interp(np.asarray(t, float), x, np.array(y) / 1e4)


def key_rate_durations(port, curve, keys=KEYS):
    v0 = port.value(curve)
    out = {}
    for k in keys:
        up = port.value(curve.shifted(key_rate_shift(k, 1.0, keys)))
        dn = port.value(curve.shifted(key_rate_shift(k, -1.0, keys)))
        out[f"KRD {k}y"] = -(up - dn) / (2 * 1e-4 * v0)
    return out


def horizon_return(port, curve, horizon=1.0):
    """12-month return with the curve unchanged. Total = (value in one year on the same curve with
    maturities one year shorter + coupons received) / value today - 1. Carry = the same calculation
    holding each bond's yield to maturity constant; roll-down = total - carry. Coupons are not reinvested."""
    v0 = port.value(curve)
    tot_end, carry_end = 0.0, 0.0
    for b, n in zip(port.bonds, port.notionals):
        k = n / b.face
        t, cf = b.cashflows()
        cpn = cf[t <= horizon + 1e-9].sum()
        y0 = b.ytm(b.price(curve))
        if b.maturity <= horizon + 1e-9:
            end_rolled = end_carry = 0.0
        else:
            end_rolled = b.price(curve, settle=horizon)
            end_carry = b.price_from_ytm(y0, settle=horizon)
        tot_end += k * (end_rolled + cpn)
        carry_end += k * (end_carry + cpn)
    total, carry = tot_end / v0 - 1, carry_end / v0 - 1
    return {"Total": total, "Carry": carry, "Roll-down": total - carry}
