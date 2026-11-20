import numpy as np

from finai.research.v56.core import Config
from finai.research.v56.portfolio_v007 import alpha_preserving_weights


def _book(seed: int, n: int = 60):
    rng = np.random.default_rng(seed)
    sectors = np.repeat(list("ABCDEF"), n // 6)
    return rng, sectors


def test_turnover_cap_holds_after_beta_adjustment_with_drifting_betas():
    cfg = Config(position_limit=0.05, beta_exposure_limit=0.10, rebalance_turnover_limit=0.25)
    for seed in range(40):
        rng, sectors = _book(seed)
        beta_old = rng.uniform(0.5, 1.5, len(sectors))
        previous, _ = alpha_preserving_weights(rng.normal(size=len(sectors)), np.zeros(len(sectors)),
                                               beta_old, sectors, cfg)
        for _ in range(6):  # build up a full book under the old betas
            previous, _ = alpha_preserving_weights(rng.normal(size=len(sectors)), previous, beta_old, sectors, cfg)
        beta_new = beta_old + rng.normal(0, 0.3, len(sectors))  # betas re-estimated
        weights, status = alpha_preserving_weights(rng.normal(size=len(sectors)), previous, beta_new, sectors, cfg)
        assert np.abs(weights - previous).sum() <= cfg.rebalance_turnover_limit + 1e-9
        assert abs(weights.sum()) < 1e-9
        if status == "active":
            assert abs(weights @ beta_new) <= cfg.beta_exposure_limit + 1e-9


def test_extreme_beta_drift_keeps_turnover_cap_and_reports_it():
    cfg = Config(position_limit=0.10, beta_exposure_limit=0.01, rebalance_turnover_limit=0.02)
    sectors = np.repeat(list("ABC"), 6)
    previous = np.tile([0.05, 0.05, 0.0, 0.0, -0.05, -0.05], 3)
    beta = np.tile([3.0, 3.0, 1.0, 1.0, 0.1, 0.1], 3)  # previous book now has large beta
    weights, status = alpha_preserving_weights(np.tile(np.arange(6.0), 3), previous, beta, sectors, cfg)
    assert np.abs(weights - previous).sum() <= cfg.rebalance_turnover_limit + 1e-9
    assert status == "beta_drift_limited"
