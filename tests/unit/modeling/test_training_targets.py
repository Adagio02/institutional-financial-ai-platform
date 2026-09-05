import math

import pandas as pd
import pytest

from finai.application.services.training_service import (
    TrainingService,
)
from finai.domain.modeling.enums import (
    PredictionTask,
)


def test_classification_target_uses_next_period_return() -> None:
    frame = pd.DataFrame(
        {
            "simple_return": [
                0.01,
                -0.02,
                0.03,
                -0.01,
            ]
        }
    )

    target_column = TrainingService._add_target(
        frame=frame,
        prediction_task=PredictionTask.CLASSIFICATION,
    )

    assert target_column == "target_positive_return"

    # Row 0 predicts row 1, whose return is negative.
    assert frame[target_column].iloc[0] == 0.0

    # Row 1 predicts row 2, whose return is positive.
    assert frame[target_column].iloc[1] == 1.0

    # Row 2 predicts row 3, whose return is negative.
    assert frame[target_column].iloc[2] == 0.0

    # The final row has no future return available.
    assert math.isnan(frame[target_column].iloc[3])


def test_regression_target_uses_next_period_return() -> None:
    frame = pd.DataFrame(
        {
            "simple_return": [
                0.01,
                -0.02,
                0.03,
                -0.01,
            ]
        }
    )

    target_column = TrainingService._add_target(
        frame=frame,
        prediction_task=PredictionTask.REGRESSION,
    )

    assert target_column == "target_next_return"

    assert frame[target_column].iloc[0] == pytest.approx(-0.02)
    assert frame[target_column].iloc[1] == pytest.approx(0.03)
    assert frame[target_column].iloc[2] == pytest.approx(-0.01)

    # The final row has no next-period return.
    assert math.isnan(frame[target_column].iloc[3])


def test_classification_target_does_not_use_current_return() -> None:
    frame = pd.DataFrame(
        {
            "simple_return": [
                0.50,
                -0.25,
                0.10,
            ]
        }
    )

    target_column = TrainingService._add_target(
        frame=frame,
        prediction_task=PredictionTask.CLASSIFICATION,
    )

    # Although the first row itself is positive, its target is based
    # on the second row, which is negative.
    assert frame[target_column].iloc[0] == 0.0

    # Although the second row itself is negative, its target is based
    # on the third row, which is positive.
    assert frame[target_column].iloc[1] == 1.0


def test_regression_target_does_not_modify_simple_return() -> None:
    original_returns = pd.Series(
        [
            0.01,
            -0.02,
            0.03,
        ],
        name="simple_return",
    )

    frame = pd.DataFrame(
        {
            "simple_return": original_returns.copy(),
        }
    )

    TrainingService._add_target(
        frame=frame,
        prediction_task=PredictionTask.REGRESSION,
    )

    pd.testing.assert_series_equal(
        frame["simple_return"],
        original_returns,
    )


def test_add_target_requires_simple_return_column() -> None:
    frame = pd.DataFrame(
        {
            "log_return": [
                0.01,
                -0.02,
            ]
        }
    )

    with pytest.raises(
        ValueError,
        match="requires simple_return",
    ):
        TrainingService._add_target(
            frame=frame,
            prediction_task=PredictionTask.CLASSIFICATION,
        )


def test_add_target_rejects_unsupported_task() -> None:
    frame = pd.DataFrame(
        {
            "simple_return": [
                0.01,
                -0.02,
            ]
        }
    )

    with pytest.raises(
        ValueError,
        match="Unsupported prediction task",
    ):
        TrainingService._add_target(
            frame=frame,
            prediction_task="unsupported",  # type: ignore[arg-type]
        )
