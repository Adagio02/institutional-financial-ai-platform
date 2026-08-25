from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class V32PromotionMetrics:
    balanced_accuracy: float
    macro_f1: float

    net_return: float
    trade_count: int

    maximum_drawdown: float
    sharpe_like: float

    fold_positive_fraction: float

    composite_score: float


@dataclass(
    frozen=True,
    slots=True,
)
class V32PromotionDecision:
    promote: bool
    reason: str

    candidate_score: float
    champion_score: float | None
    baseline_score: float

    improvement_over_baseline: float
    improvement_over_champion: float | None


class V32PromotionPolicy:
    def __init__(
        self,
        *,
        minimum_balanced_accuracy: float,
        minimum_macro_f1: float,
        minimum_net_return: float,
        minimum_trades: int,
        maximum_drawdown: float,
        minimum_sharpe_like: float,
        minimum_fold_positive_fraction: float,
        minimum_baseline_improvement: float,
        minimum_promotion_improvement: float,
    ) -> None:
        if not 0.0 <= minimum_balanced_accuracy <= 1.0:
            raise ValueError(
                "minimum_balanced_accuracy must "
                "be between 0 and 1."
            )

        if not 0.0 <= minimum_macro_f1 <= 1.0:
            raise ValueError(
                "minimum_macro_f1 must "
                "be between 0 and 1."
            )

        if minimum_trades < 0:
            raise ValueError(
                "minimum_trades cannot be negative."
            )

        if maximum_drawdown < 0.0:
            raise ValueError(
                "maximum_drawdown cannot be negative."
            )

        if not (
            0.0
            <= minimum_fold_positive_fraction
            <= 1.0
        ):
            raise ValueError(
                "minimum_fold_positive_fraction "
                "must be between 0 and 1."
            )

        if minimum_baseline_improvement < 0.0:
            raise ValueError(
                "minimum_baseline_improvement "
                "cannot be negative."
            )

        if minimum_promotion_improvement < 0.0:
            raise ValueError(
                "minimum_promotion_improvement "
                "cannot be negative."
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

        self._maximum_drawdown = (
            maximum_drawdown
        )

        self._minimum_sharpe_like = (
            minimum_sharpe_like
        )

        self._minimum_fold_positive_fraction = (
            minimum_fold_positive_fraction
        )

        self._minimum_baseline_improvement = (
            minimum_baseline_improvement
        )

        self._minimum_promotion_improvement = (
            minimum_promotion_improvement
        )

    def evaluate(
        self,
        *,
        candidate: V32PromotionMetrics,
        baseline_score: float,
        champion_score: float | None,
    ) -> V32PromotionDecision:
        baseline_improvement = (
            candidate.composite_score
            - baseline_score
        )

        champion_improvement = (
            None
            if champion_score is None
            else (
                candidate.composite_score
                - champion_score
            )
        )

        def reject(
            reason: str,
        ) -> V32PromotionDecision:
            return V32PromotionDecision(
                promote=False,
                reason=reason,
                candidate_score=(
                    candidate.composite_score
                ),
                champion_score=champion_score,
                baseline_score=baseline_score,
                improvement_over_baseline=(
                    baseline_improvement
                ),
                improvement_over_champion=(
                    champion_improvement
                ),
            )

        if (
            candidate.balanced_accuracy
            < self._minimum_balanced_accuracy
        ):
            return reject(
                "Candidate balanced accuracy "
                "is below the minimum."
            )

        if (
            candidate.macro_f1
            < self._minimum_macro_f1
        ):
            return reject(
                "Candidate macro F1 is below "
                "the minimum."
            )

        if (
            candidate.net_return
            <= self._minimum_net_return
        ):
            return reject(
                "Candidate net return failed "
                "the economic-performance gate."
            )

        if (
            candidate.trade_count
            < self._minimum_trades
        ):
            return reject(
                "Candidate produced too few "
                "validation trades."
            )

        if (
            candidate.maximum_drawdown
            > self._maximum_drawdown
        ):
            return reject(
                "Candidate maximum drawdown "
                "exceeds the configured limit."
            )

        if (
            candidate.sharpe_like
            < self._minimum_sharpe_like
        ):
            return reject(
                "Candidate risk-adjusted return "
                "is below the minimum."
            )

        if (
            candidate.fold_positive_fraction
            < self._minimum_fold_positive_fraction
        ):
            return reject(
                "Candidate performance is not "
                "stable across enough folds."
            )

        if (
            baseline_improvement
            < self._minimum_baseline_improvement
        ):
            return reject(
                "Candidate did not outperform "
                "the baseline by enough."
            )

        if champion_score is None:
            return V32PromotionDecision(
                promote=True,
                reason=(
                    "Candidate passed all V3.2 "
                    "research and economic gates."
                ),
                candidate_score=(
                    candidate.composite_score
                ),
                champion_score=None,
                baseline_score=baseline_score,
                improvement_over_baseline=(
                    baseline_improvement
                ),
                improvement_over_champion=None,
            )

        if (
            champion_improvement is None
            or champion_improvement
            < self._minimum_promotion_improvement
        ):
            return reject(
                "Candidate did not improve the "
                "existing champion enough."
            )

        return V32PromotionDecision(
            promote=True,
            reason=(
                "Candidate passed all V3.2 gates "
                "and improved the champion."
            ),
            candidate_score=(
                candidate.composite_score
            ),
            champion_score=champion_score,
            baseline_score=baseline_score,
            improvement_over_baseline=(
                baseline_improvement
            ),
            improvement_over_champion=(
                champion_improvement
            ),
        )