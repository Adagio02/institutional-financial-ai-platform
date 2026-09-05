from finai.application.services.v31_learning_service import (
    V31LearningService,
)
from finai.core.config import Settings


def create_v31_learning_service(
    *,
    settings: Settings,
) -> V31LearningService:
    return V31LearningService(
        database_url=(
            settings.database_url
        ),
        artifact_directory=(
            settings
            .v31_learning_artifact_directory
        ),
        minimum_rows=(
            settings
            .v31_learning_minimum_rows
        ),
        forward_horizon_bars=(
            settings
            .v31_forward_horizon_bars
        ),
        target_minimum_edge_bps=(
            settings
            .v31_target_minimum_edge_bps
        ),
        round_trip_cost_bps=(
            settings
            .v31_round_trip_cost_bps
        ),
        walk_forward_folds=(
            settings
            .v31_walk_forward_folds
        ),
        minimum_balanced_accuracy=(
            settings
            .v31_minimum_balanced_accuracy
        ),
        minimum_macro_f1=(
            settings
            .v31_minimum_macro_f1
        ),
        minimum_net_return=(
            settings
            .v31_minimum_net_return
        ),
        minimum_trades=(
            settings
            .v31_minimum_trades
        ),
        minimum_promotion_improvement=(
            settings
            .v31_minimum_promotion_improvement
        ),
        signal_probability_threshold=(
            settings
            .v31_signal_probability_threshold
        ),
        require_non_mock_data=(
            settings
            .v31_learning_require_non_mock_data
        ),
    )