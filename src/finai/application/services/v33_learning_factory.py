from __future__ import annotations

from finai.application.services.v33_learning_service import (
    V33LearningService,
)
from finai.core.config import Settings


def parse_thresholds(
    value: str,
) -> list[float]:
    values = []

    for item in value.split(","):
        normalized = item.strip()

        if not normalized:
            continue

        values.append(
            float(
                normalized
            )
        )

    if not values:
        raise ValueError(
            "Probability threshold configuration "
            "cannot be empty."
        )

    return values


def create_v33_learning_service(
    *,
    settings: Settings,
) -> V33LearningService:
    return V33LearningService(
        database_url=(
            settings.database_url
        ),
        artifact_directory=(
            settings
            .v33_learning_artifact_directory
        ),
        minimum_rows=(
            settings
            .v33_learning_minimum_rows
        ),
        holdout_fraction=(
            settings
            .v33_holdout_fraction
        ),
        forward_horizon_bars=(
            settings
            .v33_forward_horizon_bars
        ),
        target_volatility_multiplier=(
            settings
            .v33_target_volatility_multiplier
        ),
        round_trip_cost_bps=(
            settings
            .v33_round_trip_cost_bps
        ),
        walk_forward_folds=(
            settings
            .v33_walk_forward_folds
        ),
        purge_bars=(
            settings
            .v33_purge_bars
        ),
        long_probability_thresholds=(
            parse_thresholds(
                settings
                .v33_long_probability_thresholds
            )
        ),
        short_probability_thresholds=(
            parse_thresholds(
                settings
                .v33_short_probability_thresholds
            )
        ),
        minimum_balanced_accuracy=(
            settings
            .v33_minimum_balanced_accuracy
        ),
        minimum_macro_f1=(
            settings
            .v33_minimum_macro_f1
        ),
        minimum_net_return=(
            settings
            .v33_minimum_net_return
        ),
        minimum_trades=(
            settings
            .v33_minimum_trades
        ),
        maximum_drawdown=(
            settings
            .v33_maximum_drawdown
        ),
        minimum_positive_fold_fraction=(
            settings
            .v33_minimum_positive_fold_fraction
        ),
        minimum_baseline_improvement=(
            settings
            .v33_minimum_baseline_improvement
        ),
        minimum_promotion_improvement=(
            settings
            .v33_minimum_promotion_improvement
        ),
        require_non_mock_data=(
            settings
            .v33_learning_require_non_mock_data
        ),
    )