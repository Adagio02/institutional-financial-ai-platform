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


def ranked_factor_neutral_weights(
    scores: np.ndarray,
    previous: np.ndarray,
    cfg: Config,
    beta: np.ndarray,
    sectors: np.ndarray,
    volatility: np.ndarray,
) -> tuple[np.ndarray, str]:
    """Deterministic long/short construction with sector and beta neutrality."""
    scores = np.asarray(scores, float)
    beta = np.asarray(beta, float)
    volatility = np.asarray(volatility, float)
    sectors = np.asarray(sectors)
    valid = np.isfinite(scores) & np.isfinite(beta) & np.isfinite(volatility)
    if valid.sum() < max(8, int(0.8 * len(scores))) or np.nanstd(scores) < 1e-12:
        return np.zeros(len(scores)), "insufficient_signal_or_exposure_data"
    # Fill rare missing exposures from the same-date cross section; never future data.
    beta = np.where(np.isfinite(beta), beta, np.nanmedian(beta))
    volatility = np.where(np.isfinite(volatility), volatility, np.nanmedian(volatility))
    volatility = np.maximum(volatility, 1e-4)
    weights = np.zeros(len(scores))
    unique = sorted(pd.Series(sectors).dropna().unique())
    usable = [sector for sector in unique if np.sum(sectors == sector) >= 4]
    if len(usable) < 3:
        return weights, "insufficient_sector_breadth"
    sector_gross = cfg.gross_limit / len(usable)
    for sector in usable:
        indices = np.flatnonzero(sectors == sector)
        ranked = indices[np.argsort(scores[indices])]
        count = max(1, int(np.floor(len(indices) * cfg.long_fraction)))
        short_idx, long_idx = ranked[:count], ranked[-count:]
        long_scale = 1.0 / volatility[long_idx]
        short_scale = 1.0 / volatility[short_idx]
        weights[long_idx] = 0.5 * sector_gross * long_scale / long_scale.sum()
        weights[short_idx] = -0.5 * sector_gross * short_scale / short_scale.sum()
    # Remove beta exposure using beta residualized within sector. This correction
    # preserves each sector's zero net exposure.
    beta_residual = beta.copy()
    for sector in usable:
        mask = sectors == sector
        beta_residual[mask] -= beta_residual[mask].mean()
    denominator = float(beta_residual @ beta_residual)
    if denominator > 1e-12:
        weights -= float(weights @ beta) / denominator * beta_residual
    # Smooth toward the new target. Both vectors are then re-projected so the
    # result remains neutral under today's beta estimates.
    if np.abs(previous).sum() > 1e-12:
        weights = 0.50 * previous + 0.50 * weights
        if denominator > 1e-12:
            weights -= float(weights @ beta) / denominator * beta_residual
        for sector in usable:
            mask = sectors == sector
            weights[mask] -= weights[mask].mean()
    scale = min(
        1.0,
        cfg.position_limit / max(np.abs(weights).max(), 1e-12),
        cfg.gross_limit / max(np.abs(weights).sum(), 1e-12),
    )
    weights *= scale
    if np.abs(weights).sum() < 0.10:
        return np.zeros(len(scores)), "degenerate_after_neutralization"
    return weights, "active"


def simulate_ranked(predictions: pd.DataFrame, cfg: Config) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, positions, previous_map = [], [], {}
    grouped = list(predictions.groupby("timestamp", sort=True))
    for group_index, (date, section) in enumerate(grouped):
        if group_index % cfg.rebalance_every:
            continue
        section = section.sort_values("symbol").copy()
        previous = np.array([previous_map.get(symbol, 0.0) for symbol in section.symbol])
        weights, status = ranked_factor_neutral_weights(
            section.ensemble.to_numpy(float), previous, cfg,
            section.beta.to_numpy(float), section.sector.to_numpy(),
            section.volatility.to_numpy(float),
        )
        turnover = float(np.abs(weights - previous).sum())
        gross = float(np.nansum(weights * section.forward_return.to_numpy(float)))
        cost = turnover * cfg.cost_bps / 10000.0
        net = gross - cost
        rows.append({
            "timestamp": date, "gross_return": gross, "cost": cost,
            "net_return": net, "turnover": turnover, "construction_status": status,
            "gross_exposure": float(np.abs(weights).sum()),
            "net_exposure": float(weights.sum()), "beta_exposure": float(weights @ section.beta.to_numpy(float)),
        })
        for symbol, weight, signal in zip(section.symbol, weights, section.ensemble):
            positions.append({"timestamp": date, "symbol": symbol, "weight": weight, "signal": signal})
            previous_map[symbol] = weight
    return pd.DataFrame(rows), pd.DataFrame(positions)


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


def metrics(ledger: pd.DataFrame, rebalance_every: int | None = None) -> dict:
    r = ledger.net_return.fillna(0.0)
    equity = (1.0 + r).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    std = float(r.std(ddof=1))
    if rebalance_every is None:
        rebalance_every = int(getattr(ledger, "attrs", {}).get("rebalance_every", 1))
    annual_periods = 252.0 / max(1, int(rebalance_every))
    sharpe = float(np.sqrt(annual_periods) * r.mean() / std) if std > 0 else 0.0
    return {
        "period_count": len(r), "cumulative_net_return": float(equity.iloc[-1] - 1.0),
        "annualized_sharpe": sharpe, "maximum_drawdown": float(drawdown.min()),
        "positive_period_fraction": float((r > 0).mean()),
        "mean_turnover": float(ledger.turnover.mean()), "total_transaction_cost": float(ledger.cost.sum()),
    }
