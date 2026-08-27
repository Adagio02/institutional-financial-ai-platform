from finai.application.services.v38_learning_service import (
    V38LearningService,
)
from finai.core.config import Settings


def parse_thresholds(
    value: str,
) -> list[float]:
    thresholds = [
        float(
            item.strip()
        )
        for item
        in value.split(",")
        if item.strip()
    ]

    if not thresholds:
        raise ValueError(
            "Threshold configuration "
            "cannot be empty."
        )

    return thresholds


def create_v38_learning_service(
    *,
    settings: Settings,
) -> V38LearningService:
    return V38LearningService(
        database_url=(
            settings.database_url
        ),
        artifact_directory=(
            settings
            .v38_learning_artifact_directory
        ),
        minimum_rows=(
            settings
            .v38_minimum_rows
        ),
        forward_horizon_bars=(
            settings
            .v38_forward_horizon_bars
        ),
        target_minimum_edge_bps=(
            settings
            .v38_target_minimum_edge_bps
        ),
        holdout_fraction=(
            settings
            .v38_holdout_fraction
        ),
        walk_forward_folds=(
            settings
            .v38_walk_forward_folds
        ),
        purge_rows=(
            settings
            .v38_purge_rows
        ),
        round_trip_cost_bps=(
            settings
            .v38_round_trip_cost_bps
        ),
        long_probability_thresholds=(
            parse_thresholds(
                settings
                .v38_long_probability_thresholds
            )
        ),
        short_probability_thresholds=(
            parse_thresholds(
                settings
                .v38_short_probability_thresholds
            )
        ),
        inner_calibration_fraction=(
            settings
            .v38_inner_calibration_fraction
        ),
        minimum_balanced_accuracy=(
            settings
            .v38_minimum_balanced_accuracy
        ),
        minimum_macro_f1=(
            settings
            .v38_minimum_macro_f1
        ),
        minimum_net_return=(
            settings
            .v38_minimum_net_return
        ),
        minimum_positive_fold_fraction=(
            settings
            .v38_minimum_positive_fold_fraction
        ),
        minimum_trades=(
            settings
            .v38_minimum_trades
        ),
        maximum_holdout_drawdown=(
            settings
            .v38_maximum_holdout_drawdown
        ),
        minimum_promotion_improvement=(
            settings
            .v38_minimum_promotion_improvement
        ),
        require_non_mock_data=True,
    )