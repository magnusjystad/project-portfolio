"""Strategic asset allocation tools for the Northbridge University Endowment (Project 5)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from pypfopt import EfficientFrontier

EQ = ["SPY", "EFA", "EEM", "VNQ"]
GOVT = ["IEF", "TLT", "TIP"]
REAL = ["GLD", "DBC"]
CLIENT = {"assets": 2.0e9, "spend": 0.045, "spend_quarters": 12, "cost": 0.004,
          "real_target": 0.049, "vol_limit": 0.12, "loss_limit": -0.20, "loss_prob": 0.05}


def add_constraints(ef: EfficientFrontier, tickers):
    idx = {t: i for i, t in enumerate(tickers)}
    ef.add_constraint(lambda w: sum(w[idx[t]] for t in EQ) >= 0.40)
    ef.add_constraint(lambda w: sum(w[idx[t]] for t in EQ) <= 0.70)
    ef.add_constraint(lambda w: sum(w[idx[t]] for t in GOVT) >= 0.15)
    ef.add_constraint(lambda w: sum(w[idx[t]] for t in REAL) <= 0.10)
    return ef


def frontier_portfolio(mu: pd.Series, S: pd.DataFrame, target_vol=None, min_vol=False):
    ef = add_constraints(EfficientFrontier(mu, S, weight_bounds=(0, 0.40)), list(mu.index))
    if min_vol:
        ef.min_volatility()
    else:
        ef.efficient_risk(target_vol)
    w = pd.Series(ef.clean_weights(cutoff=1e-5))
    return w / w.sum()


def max_return_portfolio(mu: pd.Series):
    """Highest expected return attainable under the IPS constraints (frontier end point), via an LP."""
    import cvxpy as cp
    t = list(mu.index)
    w = cp.Variable(len(t))
    ix = lambda names: [t.index(n) for n in names]
    cons = [cp.sum(w) == 1, w >= 0, w <= 0.40,
            cp.sum(w[ix(EQ)]) >= 0.40, cp.sum(w[ix(EQ)]) <= 0.70,
            cp.sum(w[ix(GOVT)]) >= 0.15, cp.sum(w[ix(REAL)]) <= 0.10]
    cp.Problem(cp.Maximize(mu.values @ w), cons).solve()
    x = np.maximum(w.value, 0)
    return pd.Series(x / x.sum(), t)


def frontier_curve(mu, S, n=40):
    """Efficient frontier points (vol, return) between the min-vol and max-return portfolios."""
    from pypfopt import EfficientFrontier
    w0 = frontier_portfolio(mu, S, min_vol=True)
    r_lo, r_hi = float(w0 @ mu), float(max_return_portfolio(mu) @ mu)
    pts = []
    for r in np.linspace(r_lo, r_hi - 1e-6, n):
        ef = add_constraints(EfficientFrontier(mu, S, weight_bounds=(0, 0.40)), list(mu.index))
        ef.efficient_return(r)
        w = pd.Series(ef.clean_weights(cutoff=1e-6))
        pts.append({"ret": float(w @ mu), "vol": float(np.sqrt(w @ S @ w))})
    return pd.DataFrame(pts)


def lognormal_params(arith_mean, vol):
    """Annual log-return mean and s.d. that reproduce an arithmetic mean and volatility."""
    s2 = np.log(1 + vol ** 2 / (1 + arith_mean) ** 2)
    return np.log(1 + arith_mean) - s2 / 2, np.sqrt(s2)


def simulate(weights: pd.Series, arith: pd.Series, vol: pd.Series, corr: pd.DataFrame,
             years=20, paths=10_000, seed=2026, client=CLIENT):
    """Quarterly Monte Carlo of the endowment.

    Asset and inflation log returns are joint normal (LTCMA arithmetic means, volatilities and
    correlations converted to log space), drawn quarterly. The portfolio is rebalanced to target each
    quarter. Each quarter: value grows, the 0.40%/yr cost is charged (0.10% a quarter) and the
    endowment pays 4.5%/4 of the trailing 12-quarter average of quarter-end values (the 12 quarters
    before inception are set to the starting value)."""
    names = list(weights.index) + ["INFL"]
    a = pd.concat([arith[weights.index], pd.Series({"INFL": arith["INFL"]})])
    v = pd.concat([vol[weights.index], pd.Series({"INFL": vol["INFL"]})])
    mu_l, sd_l = lognormal_params(a.values, v.values)
    C = corr.loc[names, names].values
    cov_q = np.outer(sd_l, sd_l) * C / 4
    mean_q = mu_l / 4
    rng = np.random.default_rng(seed)
    q = years * 4
    draws = rng.multivariate_normal(mean_q, cov_q, size=(paths, q))      # (paths, q, n+1)
    gross = np.exp(draws[..., :-1])                                       # asset gross returns
    infl = np.exp(draws[..., -1])
    port = gross @ weights.values                                         # quarterly gross portfolio return
    V0 = client["assets"]
    V = np.empty((paths, q + 1)); V[:, 0] = V0
    hist = np.full((paths, client["spend_quarters"]), V0)
    spend = np.empty((paths, q))
    for t in range(q):
        val = V[:, t] * port[:, t] * (1 - client["cost"] / 4)
        s = client["spend"] / 4 * hist.mean(axis=1)
        val = val - s
        spend[:, t] = s
        V[:, t + 1] = val
        hist = np.column_stack([hist[:, 1:], val])
    cpi = np.column_stack([np.ones(paths), np.cumprod(infl, axis=1)])
    return {"V": V, "spend": spend, "cpi": cpi, "port": port}


def mc_summary(sim, client=CLIENT):
    V, cpi, spend, port = sim["V"], sim["cpi"], sim["spend"], sim["port"]
    real_end = V[:, -1] / cpi[:, -1]
    dd = (V / np.maximum.accumulate(V, axis=1) - 1).min(axis=1)
    yr1 = port[:, :4].prod(axis=1) * (1 - client["cost"]) - 1                 # first-year return net of costs
    annual = port.reshape(port.shape[0], -1, 4).prod(axis=2) * (1 - client["cost"]) - 1
    real_spend_annual = (spend / cpi[:, 1:]).reshape(spend.shape[0], -1, 4).sum(axis=2)
    return {
        "P(real value preserved, 20y)": float((real_end >= client["assets"]).mean()),
        "Median real value after 20y ($bn)": float(np.median(real_end) / 1e9),
        "P(drawdown worse than -30%)": float((dd < -0.30).mean()),
        "Median max drawdown": float(np.median(dd)),
        "P(1-year loss worse than -20%)": float((annual < client["loss_limit"]).mean()),
        "P(1-year loss worse than -20%), year 1": float((yr1 < client["loss_limit"]).mean()),
        "Median annual net return": float(np.median(annual)),
        "Median real spending yr 1 ($m)": float(np.median(real_spend_annual[:, 0]) / 1e6),
        "Median real spending yr 20 ($m)": float(np.median(real_spend_annual[:, -1]) / 1e6),
    }, real_spend_annual
