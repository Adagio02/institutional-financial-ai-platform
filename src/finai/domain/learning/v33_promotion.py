from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class V33PromotionMetrics:
    balanced_accuracy: float
    macro_f1: float

    net_return: float
    trade_count: int

    maximum_drawdown: float

    positive_fold_fraction: float

    baseline_net_return: float

    composite_score: float


@dataclass(
    frozen=True,
    slots=True,
)
class V33PromotionDecision:
    promote: bool
    reason: str


class V33PromotionPolicy:
    def __init__(
        self,
        *,
        minimum_balanced_accuracy: float,
        minimum_macro_f1: float,
        minimum_net_return: float,
        minimum_trades: int,
        maximum_drawdown: float,
        minimum_positive_fold_fraction: float,
        minimum_baseline_improvement: float,
        minimum_champion_improvement: float,
    ) -> None:
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

        self._minimum_positive_fold_fraction = (
            minimum_positive_fold_fraction
        )

        self._minimum_baseline_improvement = (
            minimum_baseline_improvement
        )

        self._minimum_champion_improvement = (
            minimum_champion_improvement
        )

    def evaluate(
        self,
        *,
        metrics: V33PromotionMetrics,
        champion_score: float | None,
    ) -> V33PromotionDecision:
        if (
            metrics.balanced_accuracy
            < self._minimum_balanced_accuracy
        ):
            return V33PromotionDecision(
                False,
                "Balanced accuracy is below minimum.",
            )

        if (
            metrics.macro_f1
            < self._minimum_macro_f1
        ):
            return V33PromotionDecision(
                False,
                "Macro F1 is below minimum.",
            )

        if (
            metrics.net_return
            <= self._minimum_net_return
        ):
            return V33PromotionDecision(
                False,
                "Net return does not satisfy minimum.",
            )

        if (
            metrics.trade_count
            < self._minimum_trades
        ):
            return V33PromotionDecision(
                False,
                "Trade count is below minimum.",
            )

        if (
            metrics.maximum_drawdown
            > self._maximum_drawdown
        ):
            return V33PromotionDecision(
                False,
                "Maximum drawdown exceeds limit.",
            )

        if (
            metrics.positive_fold_fraction
            < self._minimum_positive_fold_fraction
        ):
            return V33PromotionDecision(
                False,
                "Walk-forward stability is insufficient.",
            )

        baseline_improvement = (
            metrics.net_return
            - metrics.baseline_net_return
        )

        if (
            baseline_improvement
            < self._minimum_baseline_improvement
        ):
            return V33PromotionDecision(
                False,
                "Candidate did not sufficiently beat baseline.",
            )

        if champion_score is not None:
            improvement = (
                metrics.composite_score
                - champion_score
            )

            if (
                improvement
                < self._minimum_champion_improvement
            ):
                return V33PromotionDecision(
                    False,
                    "Candidate did not sufficiently beat champion.",
                )

        return V33PromotionDecision(
            True,
            "Candidate satisfied all V3.3 promotion gates.",
        )