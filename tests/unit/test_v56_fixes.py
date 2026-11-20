import numpy as np
import pandas as pd
import pytest

from finai.research.v56.core import Config
from finai.research.v56.portfolio import metrics


def test_config_accepts_v007_v008_risk_fields():
    cfg = Config(beta_exposure_limit=0.10, rebalance_turnover_limit=0.25)
    assert cfg.beta_exposure_limit == 0.10 and cfg.rebalance_turnover_limit == 0.25


def test_config_rejects_overlapping_forward_returns():
    with pytest.raises(ValueError, match="rebalance_every"):
        Config(horizon=5, rebalance_every=1)
    Config(horizon=5, rebalance_every=5)  # non-overlapping is allowed


def test_sharpe_is_annualized_by_rebalance_period():
    rng = np.random.default_rng(0)
    ledger = pd.DataFrame({"net_return": rng.normal(0.001, 0.01, 200), "turnover": 0.1, "cost": 0.0})
    daily = metrics(ledger, rebalance_every=1)["annualized_sharpe"]
    weekly = metrics(ledger, rebalance_every=5)["annualized_sharpe"]
    assert np.isclose(daily / weekly, np.sqrt(5))
