from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class V31PromotionMetrics:
    balanced_accuracy: float
    macro_f1: float
    net_return: float
    trade_count: int
    composite_score: float


@dataclass(
    frozen=True,
    slots=True,
)
class V31PromotionDecision:
    promote: bool
    reason: str

    candidate_score: float
    champion_score: float | None

    improvement: float | None


class V31PromotionPolicy:
    def __init__(
        self,
        *,
        minimum_balanced_accuracy: float,
        minimum_macro_f1: float,
        minimum_net_return: float,
        minimum_trades: int,
        minimum_improvement: float,
    ) -> None:
        if minimum_balanced_accuracy < 0.0:
            raise ValueError(
                "minimum_balanced_accuracy "
                "cannot be negative."
            )

        if minimum_macro_f1 < 0.0:
            raise ValueError(
                "minimum_macro_f1 cannot "
                "be negative."
            )

        if minimum_trades < 0:
            raise ValueError(
                "minimum_trades cannot "
                "be negative."
            )

        if minimum_improvement < 0.0:
            raise ValueError(
                "minimum_improvement cannot "
                "be negative."
            )

        self._minimum_balanced_accuracy = (
            minimum_balanced_accuracy
        )

        self._minimum_macro_f1 = (
            minimum_macro_f1
        )

        self._minimum_net_return = (
            minimum_net_return
        )

        self._minimum_trades = (
            minimum_trades
        )

        self._minimum_improvement = (
            minimum_improvement
        )

    def evaluate(
        self,
        *,
        candidate: V31PromotionMetrics,
        champion_score: float | None,
    ) -> V31PromotionDecision:
        if (
            candidate.balanced_accuracy
            < self._minimum_balanced_accuracy
        ):
            return V31PromotionDecision(
                promote=False,
                reason=(
                    "Candidate balanced accuracy "
                    "is below the minimum."
                ),
                candidate_score=(
                    candidate.composite_score
                ),
                champion_score=champion_score,
                improvement=None,
            )

        if (
            candidate.macro_f1
            < self._minimum_macro_f1
        ):
            return V31PromotionDecision(
                promote=False,
                reason=(
                    "Candidate macro F1 "
                    "is below the minimum."
                ),
                candidate_score=(
                    candidate.composite_score
                ),
                champion_score=champion_score,
                improvement=None,
            )

        if (
            candidate.net_return
            <= self._minimum_net_return
        ):
            return V31PromotionDecision(
                promote=False,
                reason=(
                    "Candidate simulated net return "
                    "does not satisfy the minimum."
                ),
                candidate_score=(
                    candidate.composite_score
                ),
                champion_score=champion_score,
                improvement=None,
            )

        if (
            candidate.trade_count
            < self._minimum_trades
        ):
            return V31PromotionDecision(
                promote=False,
                reason=(
                    "Candidate produced too few "
                    "validation trades."
                ),
                candidate_score=(
                    candidate.composite_score
                ),
                champion_score=champion_score,
                improvement=None,
            )

        if champion_score is None:
            return V31PromotionDecision(
                promote=True,
                reason=(
                    "Candidate satisfied all V3.1 "
                    "bootstrap promotion requirements."
                ),
                candidate_score=(
                    candidate.composite_score
                ),
                champion_score=None,
                improvement=None,
            )

        improvement = (
            candidate.composite_score
            - champion_score
        )

        if improvement < self._minimum_improvement:
            return V31PromotionDecision(
                promote=False,
                reason=(
                    "Candidate did not improve the "
                    "champion by the required margin."
                ),
                candidate_score=(
                    candidate.composite_score
                ),
                champion_score=champion_score,
                improvement=improvement,
            )

        return V31PromotionDecision(
            promote=True,
            reason=(
                "Candidate satisfied all V3.1 "
                "requirements and improved the champion."
            ),
            candidate_score=(
                candidate.composite_score
            ),
            champion_score=champion_score,
            improvement=improvement,
        )