from datetime import (
    UTC,
    datetime,
)
from uuid import UUID

from sqlalchemy.orm import Session

from finai.application.services.market_quote_service import (
    MarketQuoteService,
)
from finai.application.services.order_service import (
    OrderService,
)
from finai.domain.execution.enums import (
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from finai.domain.market_data.enums import (
    BarInterval,
)
from finai.domain.market_data.execution_quote import (
    get_executable_reference_price,
)
from finai.domain.portfolio.risk_limits import (
    PortfolioRiskLimits,
)
from finai.domain.strategy.enums import (
    TradeProposalStatus,
)
from finai.infrastructure.database.repositories.execution_audit_repository import (
    ExecutionAuditRepository,
)
from finai.infrastructure.database.repositories.trade_proposal_repository import (
    TradeProposalRepository,
)


class ProposalExecutionService:
    def __init__(
        self,
        *,
        session: Session,
        commission_bps: float,
        slippage_bps: float,
        risk_limits: PortfolioRiskLimits,
        maximum_quote_age_seconds: int,
        quote_interval: BarInterval,
        maximum_daily_loss: float,
        synthetic_spread_bps: float,
        partial_fill_enabled: bool,
        initial_fill_fraction: float,
        execution_mode: str,
        proposal_maximum_age_seconds: int,
        maximum_price_drift_bps: float,
        manual_approval_required: bool,
    ) -> None:
        self._proposal_repository = TradeProposalRepository(session)

        self._audit_repository = ExecutionAuditRepository(session)

        self._quote_service = MarketQuoteService(
            session=session,
            maximum_quote_age_seconds=(maximum_quote_age_seconds),
            quote_interval=(quote_interval),
            synthetic_spread_bps=(synthetic_spread_bps),
        )

        self._order_service = OrderService(
            session=session,
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            risk_limits=risk_limits,
            maximum_quote_age_seconds=(maximum_quote_age_seconds),
            quote_interval=quote_interval,
            maximum_daily_loss=(maximum_daily_loss),
            synthetic_spread_bps=(synthetic_spread_bps),
            partial_fill_enabled=(partial_fill_enabled),
            initial_fill_fraction=(initial_fill_fraction),
            execution_mode=(execution_mode),
        )

        self._proposal_maximum_age_seconds = proposal_maximum_age_seconds

        self._maximum_price_drift_bps = maximum_price_drift_bps

        self._manual_approval_required = manual_approval_required

    def execute(
        self,
        *,
        proposal_id: UUID,
    ):
        proposal = self._proposal_repository.get_by_id(proposal_id)

        if proposal is None:
            raise LookupError(f"Trade proposal not found: {proposal_id}")

        if self._manual_approval_required:
            if proposal.status != TradeProposalStatus.APPROVED.value:
                raise ValueError("Trade proposal must be approved before execution.")

        elif proposal.status not in {
            TradeProposalStatus.APPROVED.value,
            TradeProposalStatus.PENDING_APPROVAL.value,
        }:
            raise ValueError(f"Trade proposal cannot be executed from status {proposal.status}.")

        created_at = proposal.created_at

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        proposal_age_seconds = (datetime.now(UTC) - created_at).total_seconds()

        if proposal_age_seconds > self._proposal_maximum_age_seconds:
            reason = "Trade proposal expired before execution."

            self._proposal_repository.mark_expired(
                proposal,
                reason=reason,
            )

            raise ValueError(reason)

        side = OrderSide(proposal.side)

        quote = self._quote_service.get_quote(symbol=proposal.symbol)

        current_reference_price = get_executable_reference_price(
            quote=quote,
            side=side,
        )

        if proposal.reference_price <= 0:
            raise ValueError("Proposal reference price is invalid.")

        price_drift_bps = (
            abs(current_reference_price - proposal.reference_price)
            / proposal.reference_price
            * 10_000
        )

        if price_drift_bps > self._maximum_price_drift_bps:
            reason = "Market price drift exceeds the proposal execution limit."

            self._proposal_repository.mark_execution_rejected(
                proposal,
                order_id=None,
                reason=reason,
            )

            raise ValueError(reason)

        order = self._order_service.submit(
            account_id=(proposal.account_id),
            client_order_id=(f"proposal-{proposal.id}"),
            symbol=proposal.symbol,
            side=side,
            order_type=(OrderType.MARKET),
            quantity=proposal.quantity,
            limit_price=None,
            time_in_force=(TimeInForce.DAY),
            strategy_key=(proposal.strategy_key),
        )

        if order is None:
            raise RuntimeError("OrderService returned no order.")

        if order.status == (OrderStatus.REJECTED.value):
            reason = order.rejection_reason or "Order execution was rejected."

            result = self._proposal_repository.mark_execution_rejected(
                proposal,
                order_id=order.id,
                reason=reason,
            )

        else:
            result = self._proposal_repository.mark_executed(
                proposal,
                order_id=order.id,
            )

        self._audit_repository.create(
            account_id=(proposal.account_id),
            order_id=order.id,
            event_type=("trade_proposal_execution"),
            message=("Trade proposal execution was processed."),
            event_data={
                "proposal_id": (str(proposal.id)),
                "proposal_status": (result.status),
                "order_status": (order.status),
                "price_drift_bps": (price_drift_bps),
            },
        )

        return result
