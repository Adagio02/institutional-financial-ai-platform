from datetime import (
    UTC,
    datetime,
    timedelta,
)
from uuid import UUID

from sqlalchemy.orm import Session

from finai.domain.execution.enums import (
    OrderSide,
)
from finai.domain.strategy.governance import (
    StrategyGovernanceDecision,
    StrategyGovernanceLimits,
    StrategyGovernanceSnapshot,
    evaluate_strategy_governance,
)
from finai.infrastructure.database.repositories.paper_account_repository import (
    PaperAccountRepository,
)
from finai.infrastructure.database.repositories.strategy_attribution_repository import (
    StrategyAttributionRepository,
)
from finai.infrastructure.database.repositories.strategy_policy_repository import (
    StrategyPolicyRepository,
)
from finai.infrastructure.database.repositories.strategy_position_repository import (
    StrategyPositionRepository,
)
from finai.infrastructure.database.repositories.trade_proposal_repository import (
    TradeProposalRepository,
)


class StrategyGovernanceService:
    def __init__(
        self,
        *,
        session: Session,
        default_capital_budget_fraction: float,
        default_maximum_single_proposal_fraction: float,
        default_maximum_gross_exposure_fraction: float,
        default_maximum_symbol_fraction: float,
        default_maximum_daily_loss: float,
        default_cooldown_seconds: int,
        default_maximum_active_proposals: int,
        competing_signal_resolution_enabled: bool,
    ) -> None:
        self._account_repository = PaperAccountRepository(session)

        self._policy_repository = StrategyPolicyRepository(session)

        self._position_repository = StrategyPositionRepository(session)

        self._attribution_repository = StrategyAttributionRepository(session)

        self._proposal_repository = TradeProposalRepository(session)

        self._default_capital_budget_fraction = default_capital_budget_fraction

        self._default_maximum_single_proposal_fraction = default_maximum_single_proposal_fraction

        self._default_maximum_gross_exposure_fraction = default_maximum_gross_exposure_fraction

        self._default_maximum_symbol_fraction = default_maximum_symbol_fraction

        self._default_maximum_daily_loss = default_maximum_daily_loss

        self._default_cooldown_seconds = default_cooldown_seconds

        self._default_maximum_active_proposals = default_maximum_active_proposals

        self._competing_signal_resolution_enabled = competing_signal_resolution_enabled

    def get_or_create_policy(
        self,
        *,
        account_id: UUID,
        strategy_key: str,
    ):
        normalized_key = strategy_key.strip()

        if not normalized_key:
            raise ValueError("strategy_key cannot be blank.")

        policy = self._policy_repository.get(
            account_id=account_id,
            strategy_key=normalized_key,
        )

        if policy is not None:
            return policy

        return self._policy_repository.create(
            account_id=account_id,
            strategy_key=normalized_key,
            enabled=True,
            allow_buy=True,
            allow_sell=True,
            capital_budget_fraction=(self._default_capital_budget_fraction),
            maximum_single_proposal_fraction=(self._default_maximum_single_proposal_fraction),
            maximum_gross_exposure_fraction=(self._default_maximum_gross_exposure_fraction),
            maximum_symbol_fraction=(self._default_maximum_symbol_fraction),
            maximum_daily_loss=(self._default_maximum_daily_loss),
            cooldown_seconds=(self._default_cooldown_seconds),
            maximum_active_proposals=(self._default_maximum_active_proposals),
        )

    def evaluate_new_proposal(
        self,
        *,
        account_id: UUID,
        strategy_key: str,
        symbol: str,
        side: OrderSide,
        confidence: float,
        proposed_notional: float,
    ) -> StrategyGovernanceDecision:
        account = self._account_repository.get_by_id(account_id)

        if account is None:
            raise LookupError(f"Paper account not found: {account_id}")

        policy = self.get_or_create_policy(
            account_id=account_id,
            strategy_key=strategy_key,
        )

        positions = self._position_repository.list_for_strategy(
            account_id=account_id,
            strategy_key=strategy_key,
        )

        gross_exposure = sum(
            abs(position.quantity * position.average_price) for position in positions
        )

        symbol_exposure = sum(
            abs(position.quantity * position.average_price)
            for position in positions
            if position.symbol == symbol
        )

        daily_net_pnl = self._attribution_repository.daily_net_pnl(
            account_id=account_id,
            strategy_key=strategy_key,
        )

        active_count = self._proposal_repository.count_actionable(
            account_id=account_id,
            strategy_key=strategy_key,
        )

        cooldown_active = False

        latest = self._proposal_repository.latest_executed(
            account_id=account_id,
            strategy_key=strategy_key,
            symbol=symbol,
        )

        if latest is not None and latest.executed_at is not None:
            executed_at = latest.executed_at

            if executed_at.tzinfo is None:
                executed_at = executed_at.replace(tzinfo=UTC)

            cooldown_end = executed_at + timedelta(seconds=(policy.cooldown_seconds))

            cooldown_active = datetime.now(UTC) < cooldown_end

        capital_budget = account.initial_cash * policy.capital_budget_fraction

        limits = StrategyGovernanceLimits(
            enabled=policy.enabled,
            allow_buy=policy.allow_buy,
            allow_sell=policy.allow_sell,
            capital_budget=capital_budget,
            maximum_single_proposal_fraction=(policy.maximum_single_proposal_fraction),
            maximum_gross_exposure_fraction=(policy.maximum_gross_exposure_fraction),
            maximum_symbol_fraction=(policy.maximum_symbol_fraction),
            maximum_daily_loss=(policy.maximum_daily_loss),
            maximum_active_proposals=(policy.maximum_active_proposals),
        )

        snapshot = StrategyGovernanceSnapshot(
            current_gross_exposure=(gross_exposure),
            current_symbol_exposure=(symbol_exposure),
            daily_net_pnl=(daily_net_pnl),
            active_proposal_count=(active_count),
            cooldown_active=(cooldown_active),
        )

        decision = evaluate_strategy_governance(
            side=side,
            proposed_notional=(proposed_notional),
            limits=limits,
            snapshot=snapshot,
        )

        if not decision.approved:
            return decision

        if self._competing_signal_resolution_enabled:
            return self._resolve_competing_signals(
                account_id=account_id,
                symbol=symbol,
                side=side,
                confidence=confidence,
            )

        return decision

    def _resolve_competing_signals(
        self,
        *,
        account_id: UUID,
        symbol: str,
        side: OrderSide,
        confidence: float,
    ) -> StrategyGovernanceDecision:
        proposals = self._proposal_repository.list_actionable_for_symbol(
            account_id=account_id,
            symbol=symbol,
        )

        for existing in proposals:
            if existing.side == side.value:
                continue

            if existing.confidence >= confidence:
                return StrategyGovernanceDecision(
                    approved=False,
                    reason=(
                        "A higher-confidence competing proposal already exists for this symbol."
                    ),
                )

            self._proposal_repository.mark_rejected(
                existing,
                reason=("Superseded by a higher-confidence competing proposal."),
            )

        return StrategyGovernanceDecision(
            approved=True,
            reason=None,
        )
