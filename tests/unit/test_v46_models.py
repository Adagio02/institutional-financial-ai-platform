from __future__ import annotations

import numpy as np

from finai.domain.learning.v46_models import (
    MODEL_CONFIGS,
    create_meta_model,
)
from finai.domain.learning.v46_research import (
    candidate_hash,
    selection_penalty,
)


def test_meta_models_fit_binary_problem() -> None:
    x = np.asarray(
        [
            [0.0, 0.0],
            [0.1, 0.2],
            [1.0, 1.0],
            [1.1, 1.2],
            [0.2, 0.1],
            [1.2, 1.1],
        ],
        dtype=float,
    )

    y = np.asarray(
        [0, 0, 1, 1, 0, 1],
        dtype=int,
    )

    for config in (
        MODEL_CONFIGS.values()
    ):
        model = create_meta_model(
            config
        )
        model.fit(x, y)
        probabilities = (
            model.predict_proba(x)
        )
        assert probabilities.shape == (
            len(x),
            2,
        )


def test_selection_penalty_and_hash() -> None:
    result = selection_penalty(
        [
            0.01,
            0.02,
            -0.005,
            0.01,
            0.015,
        ],
        trial_count=20,
    )

    assert (
        result[
            "selection_penalty"
        ]
        >= 0.0
    )

    candidate = {
        "horizon_bars": 15,
        "event_family": "x",
        "model_name": "y",
        "model_config": {
            "family": "logistic"
        },
        "selected_threshold": 0.6,
    }

    assert candidate_hash(
        candidate
    ) == candidate_hash(
        dict(candidate)
    )
