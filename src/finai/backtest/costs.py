import numpy as np


def estimate_transaction_cost(
    trade_fraction: np.ndarray,
    adv_fraction: np.ndarray,
    spread_bps: float = 5.0,
    impact_coefficient: float = 10.0,
) -> np.ndarray:
    linear = np.abs(trade_fraction) * spread_bps / 10000.0
    impact = impact_coefficient / 10000.0 * np.sqrt(np.maximum(adv_fraction, 0.0))
    return linear + impact
