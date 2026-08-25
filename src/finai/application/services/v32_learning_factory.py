from finai.application.services.v32_learning_service import (
    V32LearningService,
)
from finai.core.config import Settings


def create_v32_learning_service(
    *,
    settings: Settings,
) -> V32LearningService:
    return V32LearningService(
        database_url=(
            settings.database_url
        ),
        artifact_directory=(
            settings
            .v32_learning_artifact_directory
        ),
        minimum_rows=(
            settings
            .v32_learning_minimum_rows
        ),
        forward_horizon_bars=(
            settings
            .v32_forward_horizon_bars
        ),
        target_minimum_edge_bps=(
            settings
            .v32_target_minimum_edge_bps
        ),
        round_trip_cost_bps=(
            settings
            .v32_round_trip_cost_bps
        ),
        walk_forward_folds=(
            settings
            .v32_walk_forward_folds
        ),
        holdout_fraction=(
            settings
            .v32_holdout_fraction
        ),
        signal_probability_threshold=(
            settings
            .v32_signal_probability_threshold
        ),
        minimum_balanced_accuracy=(
            settings
            .v32_minimum_balanced_accuracy
        ),
        minimum_macro_f1=(
            settings
            .v32_minimum_macro_f1
        ),
        minimum_net_return=(
            settings
            .v32_minimum_net_return
        ),
        minimum_trades=(
            settings
            .v32_minimum_trades
        ),
        maximum_drawdown=(
            settings
            .v32_maximum_drawdown
        ),
        minimum_sharpe_like=(
            settings
            .v32_minimum_sharpe_like
        ),
        minimum_fold_positive_fraction=(
            settings
            .v32_minimum_fold_positive_fraction
        ),
        minimum_baseline_improvement=(
            settings
            .v32_minimum_baseline_improvement
        ),
        minimum_promotion_improvement=(
            settings
            .v32_minimum_promotion_improvement
        ),
        require_non_mock_data=(
            settings
            .v32_learning_require_non_mock_data
        ),
    )