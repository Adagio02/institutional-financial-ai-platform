import pandas as pd

from finai.application.services.v433_learning_service import V433LearningService


def test_v433_regime_labels_are_observable_feature_based() -> None:
    frame = pd.DataFrame(
        {
            "trend_strength": [-1.0, 1.0, -2.0, 2.0],
            "market_volatility": [1.0, 1.0, 3.0, 3.0],
        }
    )
    labels = V433LearningService._regime_labels(frame)
    assert len(set(labels.tolist())) == 4
