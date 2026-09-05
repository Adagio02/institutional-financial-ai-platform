from dataclasses import dataclass

from finai.domain.execution.enums import (
    OrderSide,
)


@dataclass(frozen=True, slots=True)
class StrategyGovernanceLimits:
    enabled: bool

    allow_buy: bool
    allow_sell: bool

    capital_budget: float

    maximum_single_proposal_fraction: float
    maximum_gross_exposure_fraction: float
    maximum_symbol_fraction: float

    maximum_daily_loss: float

    maximum_active_proposals: int


@dataclass(frozen=True, slots=True)
class StrategyGovernanceSnapshot:
    current_gross_exposure: float
    current_symbol_exposure: float

    daily_net_pnl: float

    active_proposal_count: int

    cooldown_active: bool


@dataclass(frozen=True, slots=True)
class StrategyGovernanceDecision:
    approved: bool
    reason: str | None


def evaluate_strategy_governance(
    *,
    side: OrderSide,
    proposed_notional: float,
    limits: StrategyGovernanceLimits,
    snapshot: StrategyGovernanceSnapshot,
) -> StrategyGovernanceDecision:
    if proposed_notional <= 0:
        return StrategyGovernanceDecision(
            approved=False,
            reason=("Proposed notional must be positive."),
        )

    if not limits.enabled:
        return StrategyGovernanceDecision(
            approved=False,
            reason="Strategy is disabled.",
        )

    if side == OrderSide.BUY and not limits.allow_buy:
        return StrategyGovernanceDecision(
            approved=False,
            reason=("Strategy policy does not allow buy proposals."),
        )

    if side == OrderSide.SELL and not limits.allow_sell:
        return StrategyGovernanceDecision(
            approved=False,
            reason=("Strategy policy does not allow sell proposals."),
        )

    if limits.capital_budget <= 0:
        return StrategyGovernanceDecision(
            approved=False,
            reason=("Strategy capital budget is not positive."),
        )

    if snapshot.cooldown_active:
        return StrategyGovernanceDecision(
            approved=False,
            reason=("Strategy symbol cooldown is still active."),
        )

    if snapshot.active_proposal_count >= limits.maximum_active_proposals:
        return StrategyGovernanceDecision(
            approved=False,
            reason=("Strategy has reached its active proposal limit."),
        )

    if snapshot.daily_net_pnl <= -abs(limits.maximum_daily_loss):
        return StrategyGovernanceDecision(
            approved=False,
            reason=("Strategy has reached its daily loss limit."),
        )

    maximum_single_notional = limits.capital_budget * limits.maximum_single_proposal_fraction

    if proposed_notional > maximum_single_notional:
        return StrategyGovernanceDecision(
            approved=False,
            reason=("Proposal exceeds the strategy single-proposal limit."),
        )

    maximum_gross_exposure = limits.capital_budget * limits.maximum_gross_exposure_fraction

    projected_gross_exposure = snapshot.current_gross_exposure + proposed_notional

    if projected_gross_exposure > maximum_gross_exposure:
        return StrategyGovernanceDecision(
            approved=False,
            reason=("Proposal would exceed the strategy gross-exposure limit."),
        )

    maximum_symbol_exposure = limits.capital_budget * limits.maximum_symbol_fraction

    projected_symbol_exposure = snapshot.current_symbol_exposure + proposed_notional

    if projected_symbol_exposure > maximum_symbol_exposure:
        return StrategyGovernanceDecision(
            approved=False,
            reason=("Proposal would exceed the strategy symbol-concentration limit."),
        )

    return StrategyGovernanceDecision(
        approved=True,
        reason=None,
    )
