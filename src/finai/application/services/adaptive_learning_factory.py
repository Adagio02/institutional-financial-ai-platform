from finai.application.services.adaptive_learning_service import (
    AdaptiveLearningService,
)
from finai.core.config import (
    Settings,
)


def create_adaptive_learning_service(
    *,
    settings: Settings,
) -> AdaptiveLearningService:
    return AdaptiveLearningService(
        database_url=(
            settings.database_url
        ),
        artifact_directory=(
            settings
            .v30_learning_artifact_directory
        ),
        minimum_rows=(
            settings
            .v30_learning_minimum_rows
        ),
        validation_fraction=(
            settings
            .v30_learning_validation_fraction
        ),
        minimum_score=(
            settings
            .v30_learning_minimum_score
        ),
        minimum_promotion_improvement=(
            settings
            .v30_learning_minimum_promotion_improvement
        ),
        signal_probability_threshold=(
            settings
            .v30_signal_probability_threshold
        ),
        require_non_mock_data=(
            settings
            .v30_learning_require_non_mock_data
        ),
    )