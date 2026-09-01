import numpy as np

from finai.application.services.v434_learning_service import V434LearningService


def test_v434_margin_abstains_on_weak_probability_separation() -> None:
    probabilities = np.asarray([[0.20, 0.29, 0.51]])
    classes = np.asarray([-1, 0, 1])

    no_margin = V434LearningService.positions_with_margin(
        probabilities=probabilities,
        classes=classes,
        long_threshold=0.50,
        short_threshold=1.0,
        margin=0.0,
    )
    with_margin = V434LearningService.positions_with_margin(
        probabilities=probabilities,
        classes=classes,
        long_threshold=0.50,
        short_threshold=1.0,
        margin=0.25,
    )

    assert no_margin.tolist() == [1]
    assert with_margin.tolist() == [0]
