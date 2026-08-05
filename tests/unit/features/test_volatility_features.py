import math

import pandas as pd
import pytest

from finai.infrastructure.features.volatility_features import (
    calculate_drawdown,
    calculate_rolling_mean,
    calculate_rolling_volatility,
)


def test_rolling_mean_requires_full_window() -> None:
    values = pd.Series([1.0, 2.0, 3.0])

    result = calculate_rolling_mean(
        values,
        window=2,
    )

    assert math.isnan(result.iloc[0])
    assert result.iloc[1] == pytest.approx(1.5)
    assert result.iloc[2] == pytest.approx(2.5)


def test_drawdown() -> None:
    prices = pd.Series([100.0, 110.0, 99.0])

    result = calculate_drawdown(prices)

    assert result.iloc[0] == 0.0
    assert result.iloc[1] == 0.0
    assert result.iloc[2] == pytest.approx(-0.1)


def test_rolling_volatility_does_not_center() -> None:
    returns = pd.Series([0.01, 0.02, -0.01, 0.03])

    result = calculate_rolling_volatility(
        returns,
        window=3,
    )

    assert math.isnan(result.iloc[0])
    assert math.isnan(result.iloc[1])
    assert not math.isnan(result.iloc[2])
