from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import (
    BaseEstimator,
    ClassifierMixin,
    clone,
)

from finai.domain.learning.v38_models import (
    create_v38_models,
)


REGIME_HIGH_VOLATILITY = "high_volatility"
REGIME_TRENDING = "trending"
REGIME_RANGE = "range"


class V39RegimeEnsemble(
    BaseEstimator,
    ClassifierMixin,
):
    def __init__(
        self,
        *,
        base_estimator: Any,
        minimum_regime_rows: int = 1_000,
    ) -> None:
        self.base_estimator = base_estimator
        self.minimum_regime_rows = (
            minimum_regime_rows
        )

    @staticmethod
    def _validate_features(
        features: pd.DataFrame,
    ) -> None:
        required = {
            "market_volatility",
            "market_momentum",
        }

        missing = (
            required
            - set(
                features.columns
            )
        )

        if missing:
            raise ValueError(
                "V3.9 regime features are "
                "missing: "
                f"{sorted(missing)}"
            )

    def _regime_labels(
        self,
        features: pd.DataFrame,
    ) -> np.ndarray:
        self._validate_features(
            features
        )

        volatility = (
            features[
                "market_volatility"
            ]
            .to_numpy(
                dtype=float
            )
        )

        momentum = (
            features[
                "market_momentum"
            ]
            .to_numpy(
                dtype=float
            )
        )

        labels = np.full(
            len(features),
            REGIME_RANGE,
            dtype=object,
        )

        high_volatility = (
            volatility
            >= self.volatility_threshold_
        )

        trending = (
            (~high_volatility)
            & (
                np.abs(
                    momentum
                )
                >= (
                    self
                    .momentum_threshold_
                )
            )
        )

        labels[
            high_volatility
        ] = (
            REGIME_HIGH_VOLATILITY
        )

        labels[
            trending
        ] = REGIME_TRENDING

        return labels

    @staticmethod
    def _align_probabilities(
        *,
        probabilities: np.ndarray,
        source_classes: np.ndarray,
        target_classes: np.ndarray,
    ) -> np.ndarray:
        aligned = np.zeros(
            (
                probabilities.shape[0],
                len(
                    target_classes
                ),
            ),
            dtype=float,
        )

        target_index = {
            int(
                label
            ): index
            for index, label
            in enumerate(
                target_classes
            )
        }

        for source_index, label in enumerate(
            source_classes
        ):
            normalized_label = int(
                label
            )

            if (
                normalized_label
                not in target_index
            ):
                continue

            aligned[
                :,
                target_index[
                    normalized_label
                ],
            ] = probabilities[
                :,
                source_index,
            ]

        return aligned

    def fit(
        self,
        X: pd.DataFrame,
        y: Any,
    ) -> V39RegimeEnsemble:
        if not isinstance(
            X,
            pd.DataFrame,
        ):
            raise TypeError(
                "V3.9 requires pandas "
                "DataFrame features."
            )

        if self.minimum_regime_rows < 100:
            raise ValueError(
                "minimum_regime_rows must "
                "be at least 100."
            )

        self._validate_features(
            X
        )

        target = np.asarray(
            y,
            dtype=int,
        )

        if len(target) != len(X):
            raise ValueError(
                "Feature and target row counts "
                "do not match."
            )

        self.feature_names_in_ = np.asarray(
            X.columns,
            dtype=object,
        )

        self.volatility_threshold_ = float(
            np.nanmedian(
                X[
                    "market_volatility"
                ]
                .to_numpy(
                    dtype=float
                )
            )
        )

        absolute_momentum = np.abs(
            X[
                "market_momentum"
            ]
            .to_numpy(
                dtype=float
            )
        )

        self.momentum_threshold_ = float(
            np.nanmedian(
                absolute_momentum
            )
        )

        self.global_model_ = clone(
            self.base_estimator
        )

        self.global_model_.fit(
            X,
            target,
        )

        self.classes_ = np.asarray(
            self
            .global_model_
            .classes_
        )

        self.regime_models_: dict[
            str,
            Any,
        ] = {}

        labels = self._regime_labels(
            X
        )

        for regime in (
            REGIME_HIGH_VOLATILITY,
            REGIME_TRENDING,
            REGIME_RANGE,
        ):
            mask = (
                labels
                == regime
            )

            regime_rows = int(
                np.sum(
                    mask
                )
            )

            if (
                regime_rows
                < self.minimum_regime_rows
            ):
                continue

            regime_target = target[
                mask
            ]

            if (
                len(
                    np.unique(
                        regime_target
                    )
                )
                < 2
            ):
                continue

            model = clone(
                self.base_estimator
            )

            model.fit(
                X.loc[
                    mask
                ],
                regime_target,
            )

            self.regime_models_[
                regime
            ] = model

        return self

    def predict_proba(
        self,
        X: pd.DataFrame,
    ) -> np.ndarray:
        if not isinstance(
            X,
            pd.DataFrame,
        ):
            raise TypeError(
                "V3.9 requires pandas "
                "DataFrame features."
            )

        labels = self._regime_labels(
            X
        )

        global_probabilities = (
            self
            .global_model_
            .predict_proba(
                X
            )
        )

        output = (
            self
            ._align_probabilities(
                probabilities=(
                    global_probabilities
                ),
                source_classes=np.asarray(
                    self
                    .global_model_
                    .classes_
                ),
                target_classes=(
                    self.classes_
                ),
            )
        )

        for regime, model in (
            self
            .regime_models_
            .items()
        ):
            mask = (
                labels
                == regime
            )

            if not np.any(
                mask
            ):
                continue

            regime_features = X.loc[
                mask
            ]

            probabilities = (
                model.predict_proba(
                    regime_features
                )
            )

            aligned = (
                self
                ._align_probabilities(
                    probabilities=(
                        probabilities
                    ),
                    source_classes=(
                        np.asarray(
                            model.classes_
                        )
                    ),
                    target_classes=(
                        self.classes_
                    ),
                )
            )

            output[
                mask
            ] = aligned

        return output

    def predict(
        self,
        X: pd.DataFrame,
    ) -> np.ndarray:
        probabilities = (
            self.predict_proba(
                X
            )
        )

        indexes = np.argmax(
            probabilities,
            axis=1,
        )

        return self.classes_[
            indexes
        ]


def create_v39_models(
    *,
    minimum_regime_rows: int,
) -> dict[str, V39RegimeEnsemble]:
    base_models = (
        create_v38_models()
    )

    return {
        (
            "regime_"
            + name
        ): V39RegimeEnsemble(
            base_estimator=model,
            minimum_regime_rows=(
                minimum_regime_rows
            ),
        )
        for name, model
        in base_models.items()
    }