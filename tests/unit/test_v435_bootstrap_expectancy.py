import numpy as np

from finai.application.services.v435_learning_service import V435LearningService


def test_v435_bootstrap_lower_bound_is_positive_for_positive_sample() -> None:
    values = np.asarray([0.001, 0.002, 0.0015, 0.003] * 20)
    lower = V435LearningService.bootstrap_mean_lower_bound(values)
    assert lower > 0.0


def test_v435_bootstrap_lower_bound_is_negative_for_negative_sample() -> None:
    values = np.asarray([-0.001, -0.002, -0.0015, -0.003] * 20)
    lower = V435LearningService.bootstrap_mean_lower_bound(values)
    assert lower < 0.0
