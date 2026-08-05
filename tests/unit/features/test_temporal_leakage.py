import pandas as pd

from finai.infrastructure.features.return_features import (
    calculate_simple_return,
)
from finai.infrastructure.features.volatility_features import (
    calculate_rolling_mean,
)


def test_future_change_does_not_modify_past_return() -> None:
    original = pd.Series([100.0, 101.0, 102.0, 103.0])

    modified = original.copy()
    modified.iloc[-1] = 10_000.0

    original_result = calculate_simple_return(original)

    modified_result = calculate_simple_return(modified)

    assert original_result.iloc[1] == (modified_result.iloc[1])

    assert original_result.iloc[2] == (modified_result.iloc[2])


def test_future_change_does_not_modify_past_average() -> None:
    original = pd.Series([100.0, 101.0, 102.0, 103.0])

    modified = original.copy()
    modified.iloc[-1] = 10_000.0

    original_result = calculate_rolling_mean(
        original,
        window=3,
    )

    modified_result = calculate_rolling_mean(
        modified,
        window=3,
    )

    assert original_result.iloc[2] == (modified_result.iloc[2])
