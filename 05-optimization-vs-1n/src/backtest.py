"""Rolling-window backtest of six portfolio construction methods (Project 6)."""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from pypfopt import BlackLittermanModel, EfficientFrontier, risk_models
from scipy.optimize import minimize

MAX_W = 0.40
BL_PRIOR = {"SPY": .35, "EFA": .15, "EEM": .05, "IEF": .15, "TLT": .05, "TIP": .05,
            "LQD": .10, "HYG": .05, "VNQ": .02, "GLD": .02, "DBC": .01}
STRATEGIES = ["1/N", "60/40", "Min variance", "Max Sharpe", "Risk parity", "Black-Litterman"]


def w_equal(win, rf, tickers):
    return pd.Series(1 / len(tickers), tickers)


def w_6040(win, rf, tickers):
    w = pd.Series(0.0, tickers)
    w["SPY"], w["IEF"] = 0.6, 0.4
    return w


def w_minvar(win, rf, tickers):
    S = risk_models.CovarianceShrinkage(win, returns_data=True, frequency=12).ledoit_wolf()
    ef = EfficientFrontier(None, S, weight_bounds=(0, MAX_W))
    ef.min_volatility()
    return pd.Series(ef.clean_weights(cutoff=1e-6))[tickers]


def w_maxsharpe(win, rf, tickers):
    """Naive tangency portfolio: sample means and sample covariance, long-only, 40% cap."""
    mu = win.mean() * 12
    S = win.cov() * 12
    rf_a = rf.mean() * 12
    if (mu <= rf_a).all():  # no asset beats cash: tangency undefined -> lowest-variance asset mix
        return w_minvar(win, rf, tickers)
    ef = EfficientFrontier(mu, S, weight_bounds=(0, MAX_W))
    ef.max_sharpe(risk_free_rate=rf_a)
    return pd.Series(ef.clean_weights(cutoff=1e-6))[tickers]


def erc(S: np.ndarray, cap=MAX_W) -> np.ndarray:
    """Equal risk contribution: minimise 0.5 w'Sw - (1/n) sum log w (Spinu 2013), rescale.
    If the cap binds, solve the constrained least-squares version instead."""
    n = len(S)
    f = lambda y: 0.5 * y @ S @ y - np.log(y).sum() / n
    g = lambda y: S @ y - 1 / (n * y)
    y = minimize(f, np.full(n, 1 / n), jac=g, bounds=[(1e-10, None)] * n,
                 method="L-BFGS-B", options={"ftol": 1e-15, "gtol": 1e-12, "maxiter": 5000}).x
    w = y / y.sum()
    if w.max() <= cap + 1e-9:
        return w

    def obj(w):
        rc = w * (S @ w)
        return ((rc[:, None] - rc[None, :]) ** 2).sum() * 1e8
    res = minimize(obj, np.minimum(w, cap) / np.minimum(w, cap).sum(), method="SLSQP",
                   bounds=[(0, cap)] * n,
                   constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}])
    return res.x


def w_riskparity(win, rf, tickers):
    return pd.Series(erc(win.cov().values * 12), tickers)


def momentum_12_1(win):
    """Cumulative return over months t-12..t-2 (skip the most recent month)."""
    return (1 + win.iloc[-12:-1]).prod() - 1


def w_bl(win, rf, tickers, delta=2.5, tau=0.05, view=0.03, conf=0.5):
    S = win.cov() * 12
    prior = pd.Series(BL_PRIOR)[tickers]
    pi = delta * S @ prior
    mom = momentum_12_1(win).sort_values()
    P = pd.Series(0.0, tickers)
    P[mom.index[-3:]] = 1 / 3
    P[mom.index[:3]] = -1 / 3
    bl = BlackLittermanModel(S, pi=pi, P=P.values.reshape(1, -1), Q=np.array([view]),
                             omega="idzorek", view_confidences=[conf], tau=tau,
                             risk_aversion=delta)
    ef = EfficientFrontier(bl.bl_returns(), bl.bl_cov(), weight_bounds=(0, MAX_W))
    ef.max_quadratic_utility(risk_aversion=delta)
    return pd.Series(ef.clean_weights(cutoff=1e-6))[tickers]


METHODS = dict(zip(STRATEGIES, [w_equal, w_6040, w_minvar, w_maxsharpe, w_riskparity, w_bl]))


def run(R: pd.DataFrame, rf: pd.Series, window=60, cost_bps=10.0, start=None, strategies=None):
    """Monthly rebalanced backtest.

    R: monthly simple returns (index month-end). Weights for month t use only returns up
    to month t-1. Turnover is |target - drifted weights|; the initial purchase is not
    charged. Returns dict with gross/net returns, weights and turnover per strategy."""
    tickers = list(R.columns)
    strategies = strategies or STRATEGIES
    idx = R.index[window:]
    if start is not None:
        idx = idx[idx >= pd.Timestamp(start)]
    out = {}
    for name in strategies:
        f = METHODS[name]
        W, gross, to = {}, {}, {}
        prev_drift = None
        for t in idx:
            i = R.index.get_loc(t)
            win = R.iloc[i - window:i]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                w = f(win, rf.loc[win.index], tickers).clip(lower=0)
            w = w / w.sum()
            r = R.loc[t]
            gross[t] = float(w @ r)
            to[t] = 0.0 if prev_drift is None else float((w - prev_drift).abs().sum())
            prev_drift = w * (1 + r) / (1 + gross[t])
            W[t] = w
        gross = pd.Series(gross)
        to = pd.Series(to)
        out[name] = {"weights": pd.DataFrame(W).T, "gross": gross, "turnover": to,
                     "net": gross - to * cost_bps / 1e4}
    return out


def stats(r: pd.Series, rf: pd.Series, turnover=None, weights=None) -> dict:
    ex = r - rf.loc[r.index]
    wealth = (1 + r).cumprod()
    mdd = (wealth / wealth.cummax() - 1).min()
    cagr = wealth.iloc[-1] ** (12 / len(r)) - 1
    down = np.sqrt((np.minimum(ex, 0) ** 2).mean()) * np.sqrt(12)
    d = {"Ann. return": cagr, "Volatility": r.std() * np.sqrt(12),
         "Sharpe": ex.mean() / ex.std() * np.sqrt(12),
         "Sortino": ex.mean() * 12 / down, "Max drawdown": mdd, "Calmar": cagr / abs(mdd)}
    if turnover is not None:
        d["Avg monthly turnover"] = turnover.iloc[1:].mean()
    if weights is not None:
        d["Effective N"] = (1 / (weights ** 2).sum(axis=1)).mean()
    return d


def sharpe(x):
    return x.mean() / x.std(ddof=1) * np.sqrt(12)


def bootstrap_sharpe_diff(ex_a: pd.Series, ex_b: pd.Series, reps=5000, seed=7):
    """Stationary bootstrap (Politis & Romano 1994) of Sharpe(a) - Sharpe(b) on paired
    monthly excess returns. Mean block length from Politis & White (2004) via `arch`.
    Two-sided p-value from the re-centred bootstrap distribution."""
    from arch.bootstrap import StationaryBootstrap, optimal_block_length
    X = pd.concat([ex_a, ex_b], axis=1).dropna().values
    bl = float(optimal_block_length(X)["stationary"].mean())
    bs = StationaryBootstrap(bl, X, seed=seed)
    d_hat = sharpe(X[:, 0]) - sharpe(X[:, 1])
    draws = np.array([sharpe(x[0][:, 0]) - sharpe(x[0][:, 1])
                      for x, _ in bs.bootstrap(reps)])
    p = float(np.mean(np.abs(draws - d_hat) >= abs(d_hat)))
    return {"diff": d_hat, "p_value": p, "block_length": bl,
            "ci_low": float(np.percentile(draws, 2.5)), "ci_high": float(np.percentile(draws, 97.5))}
