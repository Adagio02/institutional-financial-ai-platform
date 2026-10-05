from __future__ import annotations

import numpy as np
import pandas as pd

from .core import Config
from .portfolio import metrics


def _project_beta_to_band(
    weights: np.ndarray,
    beta: np.ndarray,
    sectors: np.ndarray,
    limit: float,
) -> np.ndarray:
    exposure = float(weights @ beta)
    if abs(exposure) <= limit:
        return weights
    beta_residual = beta.copy()
    for sector in pd.Series(sectors).dropna().unique():
        mask = sectors == sector
        beta_residual[mask] -= beta_residual[mask].mean()
    denominator = float(beta_residual @ beta_residual)
    if denominator <= 1e-12:
        return weights
    target = np.sign(exposure) * limit
    return weights - (exposure - target) / denominator * beta_residual


def alpha_preserving_weights(
    scores: np.ndarray,
    previous: np.ndarray,
    beta: np.ndarray,
    sectors: np.ndarray,
    cfg: Config,
) -> tuple[np.ndarray, str]:
    scores = np.asarray(scores, float)
    beta = np.asarray(beta, float)
    sectors = np.asarray(sectors)
    if np.isfinite(scores).sum() < int(.8 * len(scores)) or np.nanstd(scores) < 1e-12:
        target = np.zeros(len(scores))
        status = "unwind_no_calibrated_edge"
    else:
        beta = np.where(np.isfinite(beta), beta, np.nanmedian(beta))
        usable = [s for s in sorted(pd.Series(sectors).dropna().unique()) if np.sum(sectors == s) >= 4]
        if len(usable) < 3:
            return np.zeros(len(scores)), "insufficient_sector_breadth"
        target = np.zeros(len(scores))
        sector_gross = cfg.gross_limit / len(usable)
        for sector in usable:
            idx = np.flatnonzero(sectors == sector)
            ranked = idx[np.argsort(scores[idx])]
            count = max(1, int(np.floor(len(idx) * cfg.long_fraction)))
            short_idx, long_idx = ranked[:count], ranked[-count:]
            target[long_idx] = .5 * sector_gross / count
            target[short_idx] = -.5 * sector_gross / count
        target = _project_beta_to_band(target, beta, sectors, cfg.beta_exposure_limit)
        status = "active"
    weights, limited = _turnover_limited_weights(target, np.asarray(previous, float), beta, sectors, cfg)
    if limited and status == "active":
        status = "beta_drift_limited"
    return weights, status


def _finalize(weights: np.ndarray, beta: np.ndarray, sectors: np.ndarray, cfg: Config) -> np.ndarray:
    """Beta band first, then position/gross scaling. Scaling preserves dollar and sector
    neutrality and can only shrink beta exposure, so the band still holds afterwards."""
    weights = _project_beta_to_band(weights, beta, sectors, cfg.beta_exposure_limit)
    scale = min(
        1.0,
        cfg.position_limit / max(np.abs(weights).max(), 1e-12),
        cfg.gross_limit / max(np.abs(weights).sum(), 1e-12),
    )
    return weights * scale


def _turnover_limited_weights(
    target: np.ndarray, previous: np.ndarray, beta: np.ndarray, sectors: np.ndarray, cfg: Config,
) -> tuple[np.ndarray, bool]:
    """Move from previous toward target as far as the turnover cap allows, measuring
    turnover AFTER the beta adjustment and scaling (V007 measured it before, so the
    beta step could push a rebalance over the cap). Returns (weights, beta_limited)."""
    cap = cfg.rebalance_turnover_limit
    beta = np.where(np.isfinite(beta), beta, np.nanmedian(beta) if np.isfinite(beta).any() else 1.0)

    def candidate(fraction: float) -> np.ndarray:
        return _finalize(previous + fraction * (target - previous), beta, sectors, cfg)

    def turnover(weights: np.ndarray) -> float:
        return float(np.abs(weights - previous).sum())

    full = candidate(1.0)
    if turnover(full) <= cap + 1e-12:
        return full, False
    stay = candidate(0.0)
    if turnover(stay) > cap + 1e-12:
        # Beta drift alone needs more trading than the cap allows: honour the cap and
        # move part of the way toward the beta-compliant book.
        step = cap / turnover(stay)
        return previous + step * (stay - previous), True
    low, high = 0.0, 1.0
    for _ in range(50):
        middle = (low + high) / 2.0
        if turnover(candidate(middle)) <= cap + 1e-12:
            low = middle
        else:
            high = middle
    return candidate(low), False


def simulate_v007(predictions: pd.DataFrame, cfg: Config) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, position_rows, previous_map = [], [], {}
    grouped = list(predictions.groupby("timestamp", sort=True))
    for group_index, (date, section) in enumerate(grouped):
        if group_index % cfg.rebalance_every:
            continue
        section = section.sort_values("symbol").copy()
        previous = np.array([previous_map.get(s, 0.0) for s in section.symbol])
        weights, status = alpha_preserving_weights(
            section.ensemble.to_numpy(float), previous,
            section.beta.to_numpy(float), section.sector.to_numpy(), cfg,
        )
        turnover = float(np.abs(weights - previous).sum())
        gross = float(np.nansum(weights * section.forward_return.to_numpy(float)))
        cost = turnover * cfg.cost_bps / 10000.0
        rows.append({
            "timestamp": date, "gross_return": gross, "cost": cost,
            "net_return": gross - cost, "turnover": turnover,
            "construction_status": status, "gross_exposure": float(np.abs(weights).sum()),
            "net_exposure": float(weights.sum()),
            "beta_exposure": float(weights @ section.beta.to_numpy(float)),
        })
        for symbol, weight, score in zip(section.symbol, weights, section.ensemble):
            position_rows.append({"timestamp": date, "symbol": symbol, "weight": weight, "signal": score})
            previous_map[symbol] = weight
    ledger = pd.DataFrame(rows)
    ledger.attrs["rebalance_every"] = cfg.rebalance_every
    return ledger, pd.DataFrame(position_rows)


__all__ = ["alpha_preserving_weights", "simulate_v007", "metrics"]
