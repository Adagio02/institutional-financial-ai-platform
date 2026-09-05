from fastapi.testclient import TestClient
from finai.core.config import get_settings
from finai.api.main import application
from tests.integration.test_prediction import (
    create_model_and_dataset,
)


client = TestClient(application)


def test_model_requires_card_before_production() -> None:
    model_id, _, _ = create_model_and_dataset()

    evaluation_response = client.post(f"/api/v1/models/{model_id}/production-evaluation")

    assert evaluation_response.status_code == 409


def test_model_card_and_production_evaluation() -> None:
    model_id, _, _ = create_model_and_dataset()

    settings = get_settings()
    original_threshold = settings.governance_minimum_accuracy

    try:
        settings.governance_minimum_accuracy = 0.0

        card_response = client.post(
            f"/api/v1/models/{model_id}/card",
            json={
                "summary": "Daily return direction classifier.",
                "intended_use": ("Research and simulated portfolio analysis."),
                "limitations": ("Not approved for autonomous live trading."),
            },
        )

        assert card_response.status_code == 201

        evaluation_response = client.post(f"/api/v1/models/{model_id}/production-evaluation")

        assert evaluation_response.status_code == 200

        evaluation = evaluation_response.json()

        assert evaluation["approved"] is True
        assert evaluation["artifact_verified"] is True
        assert evaluation["model_card_present"] is True

        promotion_response = client.post(f"/api/v1/models/{model_id}/promote-production")

        assert promotion_response.status_code == 200
        assert promotion_response.json()["stage"] == "production"

    finally:
        settings.governance_minimum_accuracy = original_threshold
