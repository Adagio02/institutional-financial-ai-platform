from finai.domain.learning.v31_promotion import (
    V31PromotionMetrics,
    V31PromotionPolicy,
)


def make_policy() -> V31PromotionPolicy:
    return V31PromotionPolicy(
        minimum_balanced_accuracy=0.34,
        minimum_macro_f1=0.30,
        minimum_net_return=0.0,
        minimum_trades=20,
        minimum_improvement=0.0025,
    )


def make_metrics(
    *,
    balanced_accuracy: float = 0.40,
    macro_f1: float = 0.38,
    net_return: float = 0.02,
    trade_count: int = 50,
    composite_score: float = 0.42,
) -> V31PromotionMetrics:
    return V31PromotionMetrics(
        balanced_accuracy=(
            balanced_accuracy
        ),
        macro_f1=macro_f1,
        net_return=net_return,
        trade_count=trade_count,
        composite_score=(
            composite_score
        ),
    )


def test_first_qualified_candidate_promotes() -> None:
    decision = make_policy().evaluate(
        candidate=make_metrics(),
        champion_score=None,
    )

    assert decision.promote is True


def test_negative_return_rejects_candidate() -> None:
    decision = make_policy().evaluate(
        candidate=make_metrics(
            net_return=-0.01
        ),
        champion_score=None,
    )

    assert decision.promote is False


def test_low_balanced_accuracy_rejects() -> None:
    decision = make_policy().evaluate(
        candidate=make_metrics(
            balanced_accuracy=0.30
        ),
        champion_score=None,
    )

    assert decision.promote is False


def test_too_few_trades_rejects() -> None:
    decision = make_policy().evaluate(
        candidate=make_metrics(
            trade_count=5
        ),
        champion_score=None,
    )

    assert decision.promote is False


def test_candidate_must_beat_champion() -> None:
    decision = make_policy().evaluate(
        candidate=make_metrics(
            composite_score=0.421
        ),
        champion_score=0.420,
    )

    assert decision.promote is False


def test_better_candidate_replaces_champion() -> None:
    decision = make_policy().evaluate(
        candidate=make_metrics(
            composite_score=0.43
        ),
        champion_score=0.42,
    )

    assert decision.promote is True