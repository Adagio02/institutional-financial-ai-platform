from pathlib import Path

from finai.application.services.v40_learning_service import (
    V40LearningCycleResult,
)


def test_v40_result_supports_shadow_state() -> None:
    result = V40LearningCycleResult(
        symbol="AAPL",
        interval="1m",
        winning_model="test_model",
        candidate_path=(
            "artifacts/v40/candidate.joblib"
        ),
        candidate_metadata_path=(
            "artifacts/v40/candidate.json"
        ),
        candidate_composite_score=0.25,
        historical_qualified=True,
        historical_reason="passed",
        shadow_candidate_path=(
            "artifacts/v40/shadow/"
            "shadow_candidate.joblib"
        ),
        shadow_metadata_path=(
            "artifacts/v40/shadow/"
            "shadow_candidate.json"
        ),
        champion_path=None,
        shadow_required=True,
        completed_at=(
            "2026-08-27T00:00:00+00:00"
        ),
    )

    assert result.historical_qualified
    assert result.shadow_required
    assert result.champion_path is None


def test_v40_paths_are_distinct() -> None:
    candidate = Path(
        "artifacts/v40/candidate.joblib"
    )

    shadow = Path(
        "artifacts/v40/shadow/"
        "shadow_candidate.joblib"
    )

    champion = Path(
        "artifacts/v40/champion.joblib"
    )

    assert candidate != shadow
    assert shadow != champion
    assert candidate != champion


def test_v40_historical_candidate_is_not_champion() -> None:
    result = V40LearningCycleResult(
        symbol="AAPL",
        interval="1m",
        winning_model="test_model",
        candidate_path="candidate.joblib",
        candidate_metadata_path="candidate.json",
        candidate_composite_score=1.0,
        historical_qualified=True,
        historical_reason=(
            "Historical gates passed."
        ),
        shadow_candidate_path=(
            "shadow_candidate.joblib"
        ),
        shadow_metadata_path=(
            "shadow_candidate.json"
        ),
        champion_path=None,
        shadow_required=True,
        completed_at=(
            "2026-08-27T00:00:00+00:00"
        ),
    )

    assert result.historical_qualified is True
    assert result.champion_path is None