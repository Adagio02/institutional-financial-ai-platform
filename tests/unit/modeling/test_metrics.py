import numpy as np
import pytest

from finai.domain.modeling.metrics import (
    calculate_classification_metrics,
    calculate_regression_metrics,
)


def test_classification_metrics() -> None:
    targets = np.array([0, 1, 1, 0])
    predictions = np.array([0, 1, 0, 0])
    probabilities = np.array([0.1, 0.9, 0.4, 0.2])

    metrics = calculate_classification_metrics(
        targets=targets,
        predictions=predictions,
        probabilities=probabilities,
    )

    assert metrics["accuracy"] == pytest.approx(0.75)

    assert "roc_auc" in metrics
    assert "brier_score" in metrics


def test_regression_metrics() -> None:
    targets = np.array([0.01, -0.02, 0.03])

    predictions = np.array([0.02, -0.01, 0.025])

    metrics = calculate_regression_metrics(
        targets=targets,
        predictions=predictions,
    )

    assert metrics["mae"] > 0
    assert metrics["rmse"] > 0
    assert 0 <= metrics["directional_accuracy"] <= 1
