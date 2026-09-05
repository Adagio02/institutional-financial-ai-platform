from __future__ import annotations

from finai.application.services.v38_learning_factory import (
    parse_thresholds,
)
from finai.application.services.v421_learning_service import (
    V421LearningService,
)
from finai.core.config import (
    Settings,
)


def create_v41_learning_service(
    *,
    settings: Settings,
) -> V421LearningService:
    return V421LearningService(
        database_url=(settings.database_url),
        artifact_directory=(settings.v41_learning_artifact_directory),
        shadow_directory=(settings.v41_shadow_directory),
        minimum_rows=(settings.v41_minimum_rows),
        forward_horizon_bars=(settings.v41_forward_horizon_bars),
        target_minimum_edge_bps=(settings.v41_target_minimum_edge_bps),
        holdout_fraction=(settings.v41_holdout_fraction),
        walk_forward_folds=(settings.v41_walk_forward_folds),
        purge_rows=(settings.v41_purge_rows),
        round_trip_cost_bps=(settings.v41_round_trip_cost_bps),
        long_probability_thresholds=(parse_thresholds(settings.v41_long_probability_thresholds)),
        short_probability_thresholds=(parse_thresholds(settings.v41_short_probability_thresholds)),
        inner_calibration_fraction=(settings.v41_inner_calibration_fraction),
        minimum_balanced_accuracy=(settings.v41_minimum_balanced_accuracy),
        minimum_macro_f1=(settings.v41_minimum_macro_f1),
        minimum_net_return=(settings.v41_minimum_net_return),
        minimum_positive_fold_fraction=(settings.v41_minimum_positive_fold_fraction),
        minimum_trades=(settings.v41_minimum_trades),
        maximum_holdout_drawdown=(settings.v41_maximum_holdout_drawdown),
        minimum_promotion_improvement=(settings.v41_minimum_promotion_improvement),
        minimum_regime_rows=(settings.v41_minimum_regime_rows),
        require_non_mock_data=True,
    )
