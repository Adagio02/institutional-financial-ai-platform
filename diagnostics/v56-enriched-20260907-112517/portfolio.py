from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .core import Config


def neutral_weights(
    scores: np.ndarray,
    previous: np.ndarray,
    cfg: Config,
    beta: np.ndarray | None = None,
    sectors: np.ndarray | None = None,
    volatility: np.ndarray | None = None,
) -> np.ndarray:
    n = len(scores)
    centered = scores - np.nanmean(scores)
    if not np.isfinite(centered).all() or np.abs(centered).sum() == 0:
        return np.zeros(n)
    ranked_initial = centered / np.abs(centered).sum() * cfg.gross_limit
    exposure_rows = [np.ones(n)]
    if beta is not None and np.isfinite(beta).all():
        exposure_rows.append(np.asarray(beta, float))
    if sectors is not None:
        unique_sectors = list(pd.Series(sectors).dropna().unique())
        for sector in unique_sectors[:-1]:  # last sector is redundant with dollar neutrality
            exposure_rows.append((np.asarray(sectors) == sector).astype(float))
    exposure = np.vstack(exposure_rows)
    initial = ranked_initial - exposure.T @ np.linalg.pinv(exposure @ exposure.T) @ exposure @ ranked_initial
    scale = min(
        1.0,
        cfg.position_limit / max(np.abs(initial).max(), 1e-12),
        cfg.gross_limit / max(np.abs(initial).sum(), 1e-12),
    )
    initial *= scale
    risk = np.ones(n) if volatility is None else np.maximum(np.asarray(volatility, float), 1e-4) ** 2
    constraints = [
        {"type": "eq", "fun": lambda w: float(w.sum())},
        {"type": "ineq", "fun": lambda w: float(cfg.gross_limit - np.abs(w).sum())},
    ]
    if beta is not None and np.isfinite(beta).all():
        b = np.asarray(beta, float)
        constraints.append({"type": "eq", "fun": lambda w, b=b: float(w @ b)})
    if sectors is not None:
        unique_sectors = list(pd.Series(sectors).dropna().unique())
        for sector in unique_sectors[:-1]:
            mask = np.asarray(sectors) == sector
            if 1 < mask.sum() < n:
                constraints.append({"type": "eq", "fun": lambda w, m=mask: float(w[m].sum())})
    def objective(w):
        alpha = -(w @ centered)
        risk_cost = cfg.risk_penalty * float(np.sum(risk * w * w))
        trade_cost = cfg.turnover_penalty * float(np.abs(w - previous).sum())
        return alpha + risk_cost + trade_cost
    result = minimize(
        objective, initial, method="SLSQP",
        bounds=[(-cfg.position_limit, cfg.position_limit)] * n,
        constraints=constraints, options={"maxiter": 300, "ftol": 1e-10},
    )
    if not result.success:
        # Safe failure mode is no exposure, not an unconstrained portfolio.
        return np.zeros(n)
    raw = result.x
    # No-trade band: weak changes are not worth their estimated round-trip cost.
    band = max(cfg.cost_bps / 10000.0 * 2.0, cfg.turnover_penalty / 10.0)
    # A coordinate-wise band can break factor constraints, so use it only for
    # the market-neutral-only case. The optimizer's L1 penalty handles the
    # constrained case.
    if beta is None and sectors is None:
        raw[np.abs(raw - previous) < band] = previous[np.abs(raw - previous) < band]
        raw -= raw.mean()
    return raw


def simulate(predictions: pd.DataFrame, cfg: Config) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, positions, previous_map = [], [], {}
    grouped = list(predictions.groupby("timestamp", sort=True))
    for group_index, (date, section) in enumerate(grouped):
        if group_index % cfg.rebalance_every != 0:
            continue
        section = section.sort_values("symbol").copy()
        previous = np.array([previous_map.get(s, 0.0) for s in section.symbol])
        beta = section.beta.to_numpy(float) if "beta" in section else None
        sectors = section.sector.to_numpy() if "sector" in section else None
        volatility = section.volatility.to_numpy(float) if "volatility" in section else None
        weights = neutral_weights(section.ensemble.to_numpy(float), previous, cfg, beta, sectors, volatility)
        turnover = float(np.abs(weights - previous).sum())
        gross = float(np.nansum(weights * section.forward_return.to_numpy(float)))
        cost = turnover * cfg.cost_bps / 10000.0
        net = gross - cost
        rows.append({"timestamp": date, "gross_return": gross, "cost": cost, "net_return": net, "turnover": turnover})
        for symbol, weight, signal in zip(section.symbol, weights, section.ensemble):
            positions.append({"timestamp": date, "symbol": symbol, "weight": weight, "signal": signal})
            previous_map[symbol] = weight
    return pd.DataFrame(rows), pd.DataFrame(positions)


def metrics(ledger: pd.DataFrame) -> dict:
    r = ledger.net_return.fillna(0.0)
    equity = (1.0 + r).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    std = float(r.std(ddof=1))
    sharpe = float(np.sqrt(252) * r.mean() / std) if std > 0 else 0.0
    return {
        "period_count": len(r), "cumulative_net_return": float(equity.iloc[-1] - 1.0),
        "annualized_sharpe": sharpe, "maximum_drawdown": float(drawdown.min()),
        "positive_period_fraction": float((r > 0).mean()),
        "mean_turnover": float(ledger.turnover.mean()), "total_transaction_cost": float(ledger.cost.sum()),
    }
