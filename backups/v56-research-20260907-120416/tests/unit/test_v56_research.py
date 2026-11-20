import numpy as np
import pandas as pd

from finai.research.v56.core import Config, normalize
from finai.research.v56.portfolio import neutral_weights


def test_forward_return_is_future_shift():
    frame = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=4), "symbol": "A", "close": [100, 101, 102, 104]})
    result = normalize(frame, Config(horizon=1, min_symbols=1, min_train_periods=1))
    assert np.isclose(result.iloc[0].forward_return, 0.01)
    assert pd.isna(result.iloc[-1].forward_return)


def test_weights_are_market_neutral_and_capped():
    cfg = Config(position_limit=0.20)
    weights = neutral_weights(np.array([-2., -1., 1., 2., 3., -3.]), np.zeros(6), cfg)
    assert abs(weights.sum()) < 1e-12
    assert np.abs(weights).max() <= 0.20 + 1e-12
    assert np.abs(weights).sum() <= cfg.gross_limit + 1e-12


def test_weights_are_sector_and_beta_neutral_when_supplied():
    cfg = Config(position_limit=0.30, risk_penalty=1.0)
    scores = np.array([-3., -2., 2., 3., -2.5, -1.5, 1.5, 2.5])
    beta = np.array([.8, 1.0, 1.2, 1.4, .7, .9, 1.1, 1.3])
    sectors = np.array(["A", "A", "A", "A", "B", "B", "B", "B"])
    weights = neutral_weights(scores, np.zeros(8), cfg, beta=beta, sectors=sectors)
    assert abs(weights.sum()) < 1e-7
    assert abs(weights @ beta) < 1e-7
    assert abs(weights[sectors == "A"].sum()) < 1e-7
    assert abs(weights[sectors == "B"].sum()) < 1e-7
