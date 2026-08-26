from finai.application.services.v34_learning_service import (
    V34LearningService,
)
from finai.core.config import Settings


def parse_thresholds(
    value: str,
) -> list[float]:
    result = [
        float(
            item.strip()
        )
        for item
        in value.split(",")
        if item.strip()
    ]

    if not result:
        raise ValueError(
            "Threshold configuration "
            "cannot be empty."
        )

    return result


def create_v34_learning_service(
    *,
    settings: Settings,
) -> V34LearningService:
    return V34LearningService(
        database_url=(
            settings.database_url
        ),
        artifact_directory=(
            settings
            .v34_learning_artifact_directory
        ),
        minimum_rows=(
            settings
            .v34_learning_minimum_rows
        ),
        holdout_fraction=(
            settings
            .v34_holdout_fraction
        ),
        forward_horizon_bars=(
            settings
            .v34_forward_horizon_bars
        ),
        target_volatility_multiplier=(
            settings
            .v34_target_volatility_multiplier
        ),
        round_trip_cost_bps=(
            settings
            .v34_round_trip_cost_bps
        ),
        walk_forward_folds=(
            settings
            .v34_walk_forward_folds
        ),
        purge_bars=(
            settings.v34_purge_bars
        ),
        long_probability_thresholds=(
            parse_thresholds(
                settings
                .v34_long_probability_thresholds
            )
        ),
        short_probability_thresholds=(
            parse_thresholds(
                settings
                .v34_short_probability_thresholds
            )
        ),
        minimum_balanced_accuracy=(
            settings
            .v34_minimum_balanced_accuracy
        ),
        minimum_macro_f1=(
            settings
            .v34_minimum_macro_f1
        ),
        minimum_net_return=(
            settings
            .v34_minimum_net_return
        ),
        minimum_trades=(
            settings
            .v34_minimum_trades
        ),
        maximum_drawdown=(
            settings
            .v34_maximum_drawdown
        ),
        minimum_positive_fold_fraction=(
            settings
            .v34_minimum_positive_fold_fraction
        ),
        minimum_baseline_improvement=(
            settings
            .v34_minimum_baseline_improvement
        ),
        minimum_promotion_improvement=(
            settings
            .v34_minimum_promotion_improvement
        ),
        require_non_mock_data=(
            settings
            .v34_learning_require_non_mock_data
        ),
        inner_calibration_fraction=(
            settings
            .v34_inner_calibration_fraction
        ),
        threshold_search_minimum_trades=(
            settings
            .v34_threshold_search_minimum_trades
        ),
        minimum_worst_fold_return=(
            settings
            .v34_minimum_worst_fold_return
        ),
        maximum_threshold_std=(
            settings
            .v34_maximum_threshold_std
        ),
        minimum_regime_return=(
            settings
            .v34_minimum_regime_return
        ),
    )