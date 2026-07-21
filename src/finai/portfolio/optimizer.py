from __future__ import annotations
from dataclasses import dataclass
import cvxpy as cp
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class OptimizationResult:
    weights: pd.Series
    status: str
    objective_value: float | None

def optimize_portfolio(
    expected_returns: pd.Series,
    covariance: pd.DataFrame,
    previous_weights: pd.Series | None = None,
    risk_aversion: float = 10.0,
    max_weight: float = 0.05,
    turnover_limit: float = 0.30,
) -> OptimizationResult:
    assets = expected_returns.index
    cov = covariance.loc[assets, assets].to_numpy()
    mu = expected_returns.to_numpy()
    n = len(assets)
    w = cp.Variable(n)
    prev = (
        previous_weights.reindex(assets).fillna(0.0).to_numpy()
        if previous_weights is not None else np.zeros(n)
    )
    objective = cp.Maximize(mu @ w - risk_aversion * cp.quad_form(w, cp.psd_wrap(cov)))
    constraints = [
        cp.sum(w) == 1,
        w >= 0,
        w <= max_weight,
        cp.norm1(w - prev) <= turnover_limit,
    ]
    problem = cp.Problem(objective, constraints)
    problem.solve(solver=cp.CLARABEL)
    values = np.zeros(n) if w.value is None else np.asarray(w.value).ravel()
    return OptimizationResult(
        weights=pd.Series(values, index=assets),
        status=str(problem.status),
        objective_value=None if problem.value is None else float(problem.value),
    )
