from __future__ import annotations

import numpy as np

from finai.domain.learning.v48_models import create_v48_models


def test_v48_models_fit_predict() -> None:
    rng = np.random.default_rng(42)
    X = rng.normal(size=(500, 18)).astype(np.float32)
    y = (0.1 * X[:, 0] - 0.05 * X[:, 1] + rng.normal(scale=0.01, size=500)).astype(np.float32)
    for _, model in create_v48_models().items():
        model.fit(X, y)
        pred = model.predict(X[:20])
        assert pred.shape == (20,)
        assert np.isfinite(pred).all()
