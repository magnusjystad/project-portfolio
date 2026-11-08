"""Zero curve construction from Treasury par yields, and Nelson-Siegel / Svensson models."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from scipy.optimize import least_squares

TENOR = {"1 Mo": 1 / 12, "1.5 Month": 1.5 / 12, "2 Mo": 2 / 12, "3 Mo": 0.25, "4 Mo": 4 / 12, "6 Mo": 0.5,
         "1 Yr": 1, "2 Yr": 2, "3 Yr": 3, "5 Yr": 5, "7 Yr": 7, "10 Yr": 10, "20 Yr": 20, "30 Yr": 30}


def par_points(row: pd.Series) -> pd.Series:
    """Par yields (decimal, bond-equivalent) indexed by maturity in years for one date."""
    s = pd.Series({TENOR[c]: row[c] / 100 for c in row.index if c in TENOR and pd.notna(row[c])})
    return s.sort_index()


class ZeroCurve:
    """Discount curve on a semiannual grid from bootstrapping cubic-spline-interpolated par yields.

    Par yields are semiannual bond-equivalent. A par bond maturing at T (multiple of 0.5) with coupon
    c satisfies 1 = c/2 * sum_{i<=n} d(t_i) + d(T). Discount factors between grid points are
    interpolated log-linearly (piecewise flat forwards)."""

    def __init__(self, par: pd.Series, max_t=30.0):
        self.par_input = par
        self.spline = CubicSpline(par.index.values, par.values, bc_type="natural")
        self.grid = np.arange(0.5, max_t + 1e-9, 0.5)
        self.par_grid = self.spline(self.grid)
        d = np.empty_like(self.grid)
        for i, c in enumerate(self.par_grid):
            d[i] = (1 - c / 2 * d[:i].sum()) / (1 + c / 2)
        self.df_grid = d

    @classmethod
    def from_discount(cls, grid, df):
        obj = cls.__new__(cls)
        obj.grid, obj.df_grid = np.asarray(grid, float), np.asarray(df, float)
        return obj

    def discount(self, t):
        t = np.asarray(t, float)
        lg = np.interp(t, np.r_[0, self.grid], np.r_[0, np.log(self.df_grid)])
        # beyond the last point extrapolate with the last zero rate
        last = -np.log(self.df_grid[-1]) / self.grid[-1]
        lg = np.where(t > self.grid[-1], -last * t, lg)
        return np.exp(lg)

    def zero_cc(self, t):
        """Continuously compounded zero rate."""
        t = np.asarray(t, float)
        return -np.log(self.discount(t)) / t

    def zero_sa(self, t):
        """Semiannually compounded zero rate."""
        t = np.asarray(t, float)
        return 2 * (self.discount(t) ** (-1 / (2 * t)) - 1)

    def par_yield(self, T):
        """Par coupon (semiannual) for maturity T on this curve."""
        n = int(round(T * 2))
        ts = np.arange(1, n + 1) / 2
        d = self.discount(ts)
        return 2 * (1 - d[-1]) / d.sum()

    def shifted(self, shift_fn):
        """New curve with continuously compounded zero rates shifted by shift_fn(t) (decimal)."""
        z = self.zero_cc(self.grid) + shift_fn(self.grid)
        return ZeroCurve.from_discount(self.grid, np.exp(-z * self.grid))


# ---------------- Nelson-Siegel family ----------------
def ns_loadings(t, lam):
    t = np.asarray(t, float)
    x = t / lam
    l1 = (1 - np.exp(-x)) / x
    return np.column_stack([np.ones_like(t), l1, l1 - np.exp(-x)])


def nss_zero(t, b0, b1, b2, b3, tau1, tau2):
    """Svensson (1994) zero rate, same parametrisation as Gurkaynak, Sack and Wright (2007)."""
    t = np.asarray(t, float)
    x1, x2 = t / tau1, t / tau2
    return (b0 + b1 * (1 - np.exp(-x1)) / x1 + b2 * ((1 - np.exp(-x1)) / x1 - np.exp(-x1))
            + b3 * ((1 - np.exp(-x2)) / x2 - np.exp(-x2)))


def nss_par(T, params):
    """Par yield (semiannual) implied by NSS continuously compounded zero rates."""
    n = int(round(T * 2))
    if n == 0:  # bills: convert the zero rate to a bond-equivalent yield
        z = nss_zero(np.array([T]), *params)[0]
        return 2 * (np.exp(z * T / (2 * T)) - 1) if T > 0 else z
    ts = np.arange(1, n + 1) / 2
    d = np.exp(-nss_zero(ts, *params) * ts)
    return 2 * (1 - d[-1]) / d.sum()


def fit_nss(par: pd.Series, starts=None):
    """Nonlinear least squares fit of NSS parameters so that model par yields match observed par yields.
    Bills (maturity < 0.5y) are matched on the zero rate converted to bond-equivalent yield."""
    T, y = par.index.values, par.values

    def resid(p):
        if p[4] <= 0.05 or p[5] <= 0.05:
            return np.full(len(T), 1.0)
        return np.array([nss_par(t, p) for t in T]) - y

    starts = starts or [[y[-1], y[0] - y[-1], b2, b3, t1, t2]
                        for b2 in (-0.02, 0.0, 0.02) for b3 in (-0.02, 0.02) for t1, t2 in ((1.0, 8.0), (2.0, 15.0), (0.5, 5.0))]
    best = None
    for s in starts:
        r = least_squares(resid, s, bounds=([0.0, -0.5, -0.5, -0.5, 0.05, 0.05], [0.3, 0.5, 0.5, 0.5, 30, 30]),
                          xtol=1e-12, ftol=1e-12)
        if best is None or r.cost < best.cost:
            best = r
    return best.x, np.sqrt(np.mean(best.fun ** 2))


def fit_ns_ols(par: pd.Series, lam=1 / 0.7308):
    """Daily Nelson-Siegel by OLS with the decay fixed (Diebold-Li 2006: 0.0609 per month = 0.7308 per year,
    so the loading parameter in years is 1/0.7308). Fitted to the observed par yields."""
    X = ns_loadings(par.index.values, lam)
    beta, *_ = np.linalg.lstsq(X, par.values, rcond=None)
    return beta
