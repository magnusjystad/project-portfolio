"""Fixed-coupon Treasury bond analytics on a ZeroCurve."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq


@dataclass
class Bond:
    maturity: float          # years
    coupon: float            # annual coupon rate, paid semiannually
    face: float = 100.0

    def cashflows(self, settle=0.0):
        n = int(round(self.maturity * 2))
        t = np.arange(1, n + 1) / 2 - settle
        cf = np.full(n, self.coupon / 2 * self.face)
        cf[-1] += self.face
        keep = t > 1e-9
        return t[keep], cf[keep]

    def price(self, curve, settle=0.0):
        t, cf = self.cashflows(settle)
        return float((cf * curve.discount(t)).sum())

    def ytm(self, price, settle=0.0):
        t, cf = self.cashflows(settle)
        f = lambda y: (cf / (1 + y / 2) ** (2 * t)).sum() - price
        return brentq(f, -0.05, 0.5)

    def price_from_ytm(self, y, settle=0.0):
        t, cf = self.cashflows(settle)
        return float((cf / (1 + y / 2) ** (2 * t)).sum())

    def mod_duration_convexity(self, y, settle=0.0):
        """Modified duration and convexity at yield y (semiannual compounding), analytic."""
        t, cf = self.cashflows(settle)
        k = 2 * t
        v = cf / (1 + y / 2) ** k
        p = v.sum()
        mac = (t * v).sum() / p
        mod = mac / (1 + y / 2)
        conv = (v * k * (k + 1) / 4).sum() / p / (1 + y / 2) ** 2
        return mod, conv


def par_bond(curve, maturity, face=100.0):
    return Bond(maturity, curve.par_yield(maturity), face)


class Portfolio:
    def __init__(self, bonds, notionals):
        """notionals: face amounts in dollars for each bond."""
        self.bonds, self.notionals = list(bonds), np.asarray(notionals, float)

    def value(self, curve, settle=0.0):
        return float(sum(n / b.face * b.price(curve, settle) for b, n in zip(self.bonds, self.notionals)))

    def mod_duration(self, curve):
        v = [n / b.face * b.price(curve) for b, n in zip(self.bonds, self.notionals)]
        d = [b.mod_duration_convexity(b.ytm(b.price(curve)))[0] for b in self.bonds]
        return float(np.dot(v, d) / sum(v))
