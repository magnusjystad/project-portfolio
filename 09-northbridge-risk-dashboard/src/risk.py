"""Risk models for the Northbridge portfolio (Project 10): VaR/ES, backtests, decomposition, stress."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

Z = {0.95: stats.norm.ppf(0.95), 0.99: stats.norm.ppf(0.99)}


# ---------- covariance ----------
def ewma_cov_series(R: np.ndarray, lam=0.94, seed_window=250):
    """RiskMetrics EWMA covariance. Returns an array C[t] = forecast for day t made with data up to t-1.
    Initialised with the sample covariance of the first `seed_window` days (zero-mean)."""
    T, n = R.shape
    C = np.empty((T, n, n))
    S = R[:seed_window].T @ R[:seed_window] / seed_window
    for t in range(T):
        C[t] = S
        x = R[t][:, None]
        S = lam * S + (1 - lam) * (x @ x.T)
    return C


# ---------- one-day VaR / ES models (losses reported as positive numbers) ----------
def hist_var_es(p: np.ndarray, alpha):
    q = np.quantile(p, 1 - alpha)
    return -q, -p[p <= q].mean()


def normal_var(sigma, alpha):
    return Z[alpha] * sigma


def normal_es(sigma, alpha):
    z = stats.norm.ppf(alpha)
    return sigma * stats.norm.pdf(z) / (1 - alpha)


def mc_t_var_es(w, cov, alphas=(0.95, 0.99), es_alpha=0.975, n=10_000, nu=5, rng=None):
    """Monte Carlo from a multivariate Student-t (nu d.o.f.) scaled to covariance `cov`."""
    rng = rng or np.random.default_rng(0)
    L = np.linalg.cholesky(cov + 1e-14 * np.eye(len(cov)))
    zz = rng.standard_normal((n, len(cov))) @ L.T
    g = rng.chisquare(nu, size=(n, 1))
    X = zz * np.sqrt((nu - 2) / g)              # covariance of X equals cov
    p = X @ w
    out = {a: -np.quantile(p, 1 - a) for a in alphas}
    q = np.quantile(p, 1 - es_alpha)
    out["ES"] = -p[p <= q].mean()
    return out


# ---------- backtests ----------
def kupiec_pof(x: int, T: int, p: float):
    """Kupiec (1995) proportion-of-failures LR test. Returns (LR, p-value)."""
    phat = x / T
    if x == 0:
        lr = -2 * (T * np.log(1 - p))
    else:
        lr = -2 * ((T - x) * np.log(1 - p) + x * np.log(p) - (T - x) * np.log(1 - phat) - x * np.log(phat))
    return lr, 1 - stats.chi2.cdf(lr, 1)


def christoffersen_ind(hits: np.ndarray):
    """Christoffersen (1998) independence LR test on the exception sequence. Returns (LR, p-value)."""
    h = hits.astype(int)
    a, b = h[:-1], h[1:]
    n00, n01 = int(((a == 0) & (b == 0)).sum()), int(((a == 0) & (b == 1)).sum())
    n10, n11 = int(((a == 1) & (b == 0)).sum()), int(((a == 1) & (b == 1)).sum())
    pi0 = n01 / (n00 + n01) if n00 + n01 else 0
    pi1 = n11 / (n10 + n11) if n10 + n11 else 0
    pi = (n01 + n11) / (n00 + n01 + n10 + n11)

    def ll(p, k0, k1):
        return (k0 * np.log(1 - p) if k0 and p < 1 else 0) + (k1 * np.log(p) if k1 and p > 0 else 0)
    lr = -2 * (ll(pi, n00 + n10, n01 + n11) - ll(pi0, n00, n01) - ll(pi1, n10, n11))
    return lr, 1 - stats.chi2.cdf(lr, 1), {"n00": n00, "n01": n01, "n10": n10, "n11": n11}


def basel_zone(exceptions_250: int):
    return "Green" if exceptions_250 <= 4 else ("Yellow" if exceptions_250 <= 9 else "Red")


# ---------- decomposition ----------
def component_var(w, cov, alpha=0.99):
    s = np.sqrt(w @ cov @ w)
    marg = cov @ w / s
    comp = w * marg * Z[alpha]
    pct_vol = w * (cov @ w) / s ** 2
    return comp, pct_vol, Z[alpha] * s


# ---------- hypothetical scenarios ----------
def bond_return(dur, conv, dy, spread_dur=0.0, ds=0.0):
    """Price change from duration and convexity. iShares quotes convexity divided by 100."""
    return -dur * dy + 0.5 * conv * 100 * dy ** 2 - spread_dur * ds
