from finai.domain.execution.enums import (
    OrderSide,
)
from finai.domain.strategy.governance import (
    StrategyGovernanceLimits,
    StrategyGovernanceSnapshot,
    evaluate_strategy_governance,
)


def build_limits() -> StrategyGovernanceLimits:
    return StrategyGovernanceLimits(
        enabled=True,
        allow_buy=True,
        allow_sell=True,
        capital_budget=25_000.0,
        maximum_single_proposal_fraction=0.25,
        maximum_gross_exposure_fraction=1.0,
        maximum_symbol_fraction=0.50,
        maximum_daily_loss=1_000.0,
        maximum_active_proposals=5,
    )


def build_snapshot() -> StrategyGovernanceSnapshot:
    return StrategyGovernanceSnapshot(
        current_gross_exposure=0.0,
        current_symbol_exposure=0.0,
        daily_net_pnl=0.0,
        active_proposal_count=0,
        cooldown_active=False,
    )


def test_valid_proposal_is_approved() -> None:
    decision = evaluate_strategy_governance(
        side=OrderSide.BUY,
        proposed_notional=5_000.0,
        limits=build_limits(),
        snapshot=build_snapshot(),
    )

    assert decision.approved is True
    assert decision.reason is None


def test_disabled_strategy_is_rejected() -> None:
    limits = StrategyGovernanceLimits(
        enabled=False,
        allow_buy=True,
        allow_sell=True,
        capital_budget=25_000.0,
        maximum_single_proposal_fraction=0.25,
        maximum_gross_exposure_fraction=1.0,
        maximum_symbol_fraction=0.50,
        maximum_daily_loss=1_000.0,
        maximum_active_proposals=5,
    )

    decision = evaluate_strategy_governance(
        side=OrderSide.BUY,
        proposed_notional=1_000.0,
        limits=limits,
        snapshot=build_snapshot(),
    )

    assert decision.approved is False


def test_daily_loss_blocks_strategy() -> None:
    snapshot = StrategyGovernanceSnapshot(
        current_gross_exposure=0.0,
        current_symbol_exposure=0.0,
        daily_net_pnl=-1_500.0,
        active_proposal_count=0,
        cooldown_active=False,
    )

    decision = evaluate_strategy_governance(
        side=OrderSide.BUY,
        proposed_notional=1_000.0,
        limits=build_limits(),
        snapshot=snapshot,
    )

    assert decision.approved is False

    assert "daily loss" in (decision.reason or "")


def test_concentration_limit_blocks_proposal() -> None:
    snapshot = StrategyGovernanceSnapshot(
        current_gross_exposure=5_000.0,
        current_symbol_exposure=12_000.0,
        daily_net_pnl=0.0,
        active_proposal_count=0,
        cooldown_active=False,
    )

    decision = evaluate_strategy_governance(
        side=OrderSide.BUY,
        proposed_notional=1_000.0,
        limits=build_limits(),
        snapshot=snapshot,
    )

    assert decision.approved is False

    assert "concentration" in (decision.reason or "")


def test_cooldown_blocks_proposal() -> None:
    snapshot = StrategyGovernanceSnapshot(
        current_gross_exposure=0.0,
        current_symbol_exposure=0.0,
        daily_net_pnl=0.0,
        active_proposal_count=0,
        cooldown_active=True,
    )

    decision = evaluate_strategy_governance(
        side=OrderSide.BUY,
        proposed_notional=1_000.0,
        limits=build_limits(),
        snapshot=snapshot,
    )

    assert decision.approved is False

    assert "cooldown" in (decision.reason or "")
