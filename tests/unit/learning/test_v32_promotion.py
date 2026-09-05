from finai.domain.learning.v32_promotion import (
    V32PromotionMetrics,
    V32PromotionPolicy,
)


def make_policy() -> V32PromotionPolicy:
    return V32PromotionPolicy(
        minimum_balanced_accuracy=0.34,
        minimum_macro_f1=0.30,
        minimum_net_return=0.0,
        minimum_trades=20,
        maximum_drawdown=0.10,
        minimum_sharpe_like=0.0,
        minimum_fold_positive_fraction=0.60,
        minimum_baseline_improvement=0.0025,
        minimum_promotion_improvement=0.005,
    )


def make_metrics() -> V32PromotionMetrics:
    return V32PromotionMetrics(
        balanced_accuracy=0.40,
        macro_f1=0.38,
        net_return=0.05,
        trade_count=50,
        maximum_drawdown=0.04,
        sharpe_like=0.8,
        fold_positive_fraction=0.80,
        composite_score=0.45,
    )


def test_first_good_candidate_can_promote() -> None:
    decision = make_policy().evaluate(
        candidate=make_metrics(),
        baseline_score=0.40,
        champion_score=None,
    )

    assert decision.promote is True


def test_negative_return_is_rejected() -> None:
    metrics = V32PromotionMetrics(
        balanced_accuracy=0.40,
        macro_f1=0.38,
        net_return=-0.01,
        trade_count=50,
        maximum_drawdown=0.04,
        sharpe_like=0.8,
        fold_positive_fraction=0.80,
        composite_score=0.45,
    )

    decision = make_policy().evaluate(
        candidate=metrics,
        baseline_score=0.40,
        champion_score=None,
    )

    assert decision.promote is False


def test_large_drawdown_is_rejected() -> None:
    metrics = V32PromotionMetrics(
        balanced_accuracy=0.40,
        macro_f1=0.38,
        net_return=0.05,
        trade_count=50,
        maximum_drawdown=0.20,
        sharpe_like=0.8,
        fold_positive_fraction=0.80,
        composite_score=0.45,
    )

    decision = make_policy().evaluate(
        candidate=metrics,
        baseline_score=0.40,
        champion_score=None,
    )

    assert decision.promote is False


def test_candidate_must_beat_baseline() -> None:
    decision = make_policy().evaluate(
        candidate=make_metrics(),
        baseline_score=0.449,
        champion_score=None,
    )

    assert decision.promote is False


def test_challenger_must_beat_champion() -> None:
    decision = make_policy().evaluate(
        candidate=make_metrics(),
        baseline_score=0.40,
        champion_score=0.448,
    )

    assert decision.promote is False