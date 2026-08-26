import pytest

from finai.application.services.v36_paper_execution_service import (
    V36PaperExecutionService,
)


def make_service(
    *,
    live_money_enabled: bool = False,
) -> V36PaperExecutionService:
    return V36PaperExecutionService(
        champion_directory=(
            "artifacts/test-v36"
        ),
        paper_order_url=(
            "http://127.0.0.1:8000/"
            "api/v1/paper/orders"
        ),
        account_id=(
            "test-account"
        ),
        quantity=1.0,
        minimum_execution_confidence=0.60,
        cooldown_seconds=300,
        maximum_market_data_age_seconds=180,
        decision_log_path=(
            "artifacts/test-v36/"
            "decisions.jsonl"
        ),
        execution_log_path=(
            "artifacts/test-v36/"
            "executions.jsonl"
        ),
        live_money_enabled=(
            live_money_enabled
        ),
    )


def test_live_money_mode_is_rejected() -> None:
    with pytest.raises(
        RuntimeError,
        match="does not permit live-money",
    ):
        make_service(
            live_money_enabled=True
        )


def test_quantity_must_be_positive() -> None:
    with pytest.raises(
        ValueError,
        match="quantity must be positive",
    ):
        V36PaperExecutionService(
            champion_directory=(
                "artifacts/test-v36"
            ),
            paper_order_url=(
                "http://127.0.0.1:8000/"
                "api/v1/paper/orders"
            ),
            account_id=(
                "test-account"
            ),
            quantity=0.0,
            minimum_execution_confidence=0.60,
            cooldown_seconds=300,
            maximum_market_data_age_seconds=180,
            decision_log_path=(
                "artifacts/test-v36/"
                "decisions.jsonl"
            ),
            execution_log_path=(
                "artifacts/test-v36/"
                "executions.jsonl"
            ),
            live_money_enabled=False,
        )


def test_service_can_start_in_paper_mode() -> None:
    service = make_service()

    assert service is not None