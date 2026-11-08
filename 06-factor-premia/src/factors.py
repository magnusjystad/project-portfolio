"""Helpers for factor statistics (Project 7)."""
import numpy as np
import pandas as pd
import statsmodels.api as sm


def max_drawdown(r: pd.Series) -> float:
    w = (1 + r).cumprod()
    return float((w / w.cummax() - 1).min())


def ann_geo(r: pd.Series) -> float:
    return float((1 + r).prod() ** (12 / len(r)) - 1)


def worst_rolling(r: pd.Series, months=60) -> float:
    """Worst annualized compounded return over any rolling `months` window."""
    roll = (1 + r).rolling(months).apply(np.prod, raw=True) ** (12 / months) - 1
    return float(roll.min())


def summary(r: pd.Series) -> dict:
    n = len(r)
    return {"Premium (ann.)": r.mean() * 12, "Volatility": r.std() * np.sqrt(12),
            "Sharpe": r.mean() / r.std() * np.sqrt(12),
            "t-stat": r.mean() / (r.std() / np.sqrt(n)),
            "Max drawdown": max_drawdown(r), "Worst 5y (ann.)": worst_rolling(r, 60), "Months": n}


def regress(y: pd.Series, X: pd.DataFrame, hac_lags=3):
    """OLS with Newey-West (HAC) standard errors."""
    d = pd.concat([y, X], axis=1).dropna()
    return sm.OLS(d.iloc[:, 0], sm.add_constant(d.iloc[:, 1:])).fit(
        cov_type="HAC", cov_kwds={"maxlags": hac_lags})


def rolling_beta(y: pd.Series, X: pd.DataFrame, col: str, window=36) -> pd.Series:
    d = pd.concat([y, X], axis=1).dropna()
    out = {}
    for i in range(window, len(d) + 1):
        s = d.iloc[i - window:i]
        b = sm.OLS(s.iloc[:, 0], sm.add_constant(s.iloc[:, 1:])).fit().params[col]
        out[s.index[-1]] = b
    return pd.Series(out)
