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

