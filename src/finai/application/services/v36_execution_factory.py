from finai.application.services.v36_paper_execution_service import (
    V36PaperExecutionService,
)
from finai.core.config import Settings


def create_v36_execution_service(
    *,
    settings: Settings,
) -> V36PaperExecutionService:
    return V36PaperExecutionService(
        champion_directory=(
            settings
            .v36_champion_directory
        ),
        paper_order_url=(
            settings
            .v36_paper_order_url
        ),
        account_id=(
            settings
            .v36_account_id
        ),
        quantity=(
            settings
            .v36_order_quantity
        ),
        minimum_execution_confidence=(
            settings
            .v36_minimum_execution_confidence
        ),
        cooldown_seconds=(
            settings
            .v36_signal_cooldown_seconds
        ),
        maximum_market_data_age_seconds=(
            settings
            .v36_maximum_market_data_age_seconds
        ),
        decision_log_path=(
            settings
            .v36_decision_log_path
        ),
        execution_log_path=(
            settings
            .v36_execution_log_path
        ),
        live_money_enabled=(
            settings
            .v36_live_money_enabled
        ),
    )