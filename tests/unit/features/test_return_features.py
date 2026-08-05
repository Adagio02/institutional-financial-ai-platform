import math

import pandas as pd
import pytest

from finai.infrastructure.features.return_features import (
    calculate_log_return,
    calculate_momentum,
    calculate_simple_return,
)


def test_simple_return() -> None:
    prices = pd.Series([100.0, 110.0, 121.0])

    result = calculate_simple_return(prices)

    assert math.isnan(result.iloc[0])
    assert result.iloc[1] == pytest.approx(0.1)
    assert result.iloc[2] == pytest.approx(0.1)


def test_log_return() -> None:
    prices = pd.Series([100.0, 110.0])

    result = calculate_log_return(prices)

    assert math.isnan(result.iloc[0])
    assert result.iloc[1] > 0.0


def test_momentum() -> None:
    prices = pd.Series([100.0, 101.0, 105.0])

    result = calculate_momentum(
        prices,
        window=2,
    )

    assert result.iloc[2] == 5.0
