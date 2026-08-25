import pytest

from finai.domain.learning.promotion_policy import (
    ModelPromotionPolicy,
)


def make_policy() -> ModelPromotionPolicy:
    return ModelPromotionPolicy(
        minimum_score=0.50,
        minimum_improvement=0.01,
    )


def test_first_qualified_model_is_promoted() -> None:
    decision = make_policy().evaluate(
        candidate_score=0.55,
        champion_score=None,
    )

    assert decision.promote is True


def test_model_below_minimum_score_is_rejected() -> None:
    decision = make_policy().evaluate(
        candidate_score=0.49,
        champion_score=None,
    )

    assert decision.promote is False


def test_candidate_must_improve_champion() -> None:
    decision = make_policy().evaluate(
        candidate_score=0.56,
        champion_score=0.55,
    )

    assert decision.promote is True

    assert decision.improvement == pytest.approx(
        0.01
    )


def test_candidate_with_insufficient_improvement_is_rejected() -> None:
    decision = make_policy().evaluate(
        candidate_score=0.555,
        champion_score=0.55,
    )

    assert decision.promote is False


def test_worse_candidate_is_rejected() -> None:
    decision = make_policy().evaluate(
        candidate_score=0.52,
        champion_score=0.56,
    )

    assert decision.promote is False