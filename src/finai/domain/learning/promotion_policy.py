from __future__ import annotations

from dataclasses import (
    dataclass,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ModelPromotionDecision:
    promote: bool
    reason: str

    candidate_score: float
    champion_score: float | None

    improvement: float | None


class ModelPromotionPolicy:
    def __init__(
        self,
        *,
        minimum_score: float,
        minimum_improvement: float,
    ) -> None:
        if not 0.0 <= minimum_score <= 1.0:
            raise ValueError(
                "minimum_score must be between 0 and 1."
            )

        if minimum_improvement < 0.0:
            raise ValueError(
                "minimum_improvement cannot be negative."
            )

        self._minimum_score = minimum_score
        self._minimum_improvement = (
            minimum_improvement
        )

    def evaluate(
        self,
        *,
        candidate_score: float,
        champion_score: float | None,
    ) -> ModelPromotionDecision:
        if not 0.0 <= candidate_score <= 1.0:
            raise ValueError(
                "candidate_score must be between 0 and 1."
            )

        if champion_score is not None:
            if not 0.0 <= champion_score <= 1.0:
                raise ValueError(
                    "champion_score must be between 0 and 1."
                )

        if candidate_score < self._minimum_score:
            return ModelPromotionDecision(
                promote=False,
                reason=(
                    "Candidate score is below the "
                    "minimum promotion score."
                ),
                candidate_score=candidate_score,
                champion_score=champion_score,
                improvement=(
                    None
                    if champion_score is None
                    else (
                        candidate_score
                        - champion_score
                    )
                ),
            )

        if champion_score is None:
            return ModelPromotionDecision(
                promote=True,
                reason=(
                    "No champion model exists and the "
                    "candidate satisfies the minimum score."
                ),
                candidate_score=candidate_score,
                champion_score=None,
                improvement=None,
            )

        improvement = (
            candidate_score
            - champion_score
        )

        if improvement < self._minimum_improvement:
            return ModelPromotionDecision(
                promote=False,
                reason=(
                    "Candidate improvement is below the "
                    "required promotion margin."
                ),
                candidate_score=candidate_score,
                champion_score=champion_score,
                improvement=improvement,
            )

        return ModelPromotionDecision(
            promote=True,
            reason=(
                "Candidate outperformed the champion "
                "by the required promotion margin."
            ),
            candidate_score=candidate_score,
            champion_score=champion_score,
            improvement=improvement,
        )