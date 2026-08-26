from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class V34PromotionMetrics:
    balanced_accuracy: float
    macro_f1: float

    net_return: float
    trade_count: int

    maximum_drawdown: float

    positive_fold_fraction: float
    worst_fold_return: float

    threshold_std: float

    worst_regime_return: float

    baseline_net_return: float

    composite_score: float


@dataclass(
    frozen=True,
    slots=True,
)
class V34PromotionDecision:
    promote: bool
    reason: str


class V34PromotionPolicy:
    def __init__(
        self,
        *,
        minimum_balanced_accuracy: float,
        minimum_macro_f1: float,
        minimum_net_return: float,
        minimum_trades: int,
        maximum_drawdown: float,
        minimum_positive_fold_fraction: float,
        minimum_worst_fold_return: float,
        maximum_threshold_std: float,
        minimum_regime_return: float,
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

        self._minimum_worst_fold_return = (
            minimum_worst_fold_return
        )

        self._maximum_threshold_std = (
            maximum_threshold_std
        )

        self._minimum_regime_return = (
            minimum_regime_return
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
        metrics: V34PromotionMetrics,
        champion_score: float | None,
    ) -> V34PromotionDecision:
        if (
            metrics.balanced_accuracy
            < self._minimum_balanced_accuracy
        ):
            return V34PromotionDecision(
                False,
                "Balanced accuracy is below minimum.",
            )

        if (
            metrics.macro_f1
            < self._minimum_macro_f1
        ):
            return V34PromotionDecision(
                False,
                "Macro F1 is below minimum.",
            )

        if (
            metrics.net_return
            <= self._minimum_net_return
        ):
            return V34PromotionDecision(
                False,
                "Net return does not satisfy minimum.",
            )

        if (
            metrics.trade_count
            < self._minimum_trades
        ):
            return V34PromotionDecision(
                False,
                "Trade count is below minimum.",
            )

        if (
            metrics.maximum_drawdown
            > self._maximum_drawdown
        ):
            return V34PromotionDecision(
                False,
                "Maximum drawdown exceeds limit.",
            )

        if (
            metrics.positive_fold_fraction
            < self._minimum_positive_fold_fraction
        ):
            return V34PromotionDecision(
                False,
                "Walk-forward stability is insufficient.",
            )

        if (
            metrics.worst_fold_return
            < self._minimum_worst_fold_return
        ):
            return V34PromotionDecision(
                False,
                "Worst walk-forward fold is too weak.",
            )

        if (
            metrics.threshold_std
            > self._maximum_threshold_std
        ):
            return V34PromotionDecision(
                False,
                "Decision thresholds are unstable.",
            )

        if (
            metrics.worst_regime_return
            < self._minimum_regime_return
        ):
            return V34PromotionDecision(
                False,
                "Candidate fails a market regime.",
            )

        baseline_improvement = (
            metrics.net_return
            - metrics.baseline_net_return
        )

        if (
            baseline_improvement
            < self._minimum_baseline_improvement
        ):
            return V34PromotionDecision(
                False,
                "Candidate does not beat baseline.",
            )

        if champion_score is not None:
            champion_improvement = (
                metrics.composite_score
                - champion_score
            )

            if (
                champion_improvement
                < self._minimum_champion_improvement
            ):
                return V34PromotionDecision(
                    False,
                    "Candidate does not sufficiently "
                    "beat the champion.",
                )

        return V34PromotionDecision(
            True,
            "Candidate passed all V3.4 "
            "real-world promotion gates.",
        )