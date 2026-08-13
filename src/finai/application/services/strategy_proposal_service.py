from uuid import UUID

from sqlalchemy.orm import Session

from finai.application.services.market_quote_service import (
    MarketQuoteService,
)
from finai.application.services.portfolio_service import (
    PortfolioService,
)
from finai.domain.execution.enums import (
    OrderSide,
)
from finai.domain.market_data.enums import (
    BarInterval,
)
from finai.domain.market_data.execution_quote import (
    get_executable_reference_price,
)
from finai.domain.strategy.enums import (
    TradeProposalStatus,
)
from finai.domain.strategy.sizing import (
    calculate_buy_size,
    calculate_sell_size,
    validate_confidence,
)
from finai.infrastructure.database.repositories.execution_audit_repository import (
    ExecutionAuditRepository,
)
from finai.infrastructure.database.repositories.instrument_repository import (
    InstrumentRepository,
)
from finai.infrastructure.database.repositories.paper_account_repository import (
    PaperAccountRepository,
)
from finai.infrastructure.database.repositories.paper_position_repository import (
    PaperPositionRepository,
)
from finai.infrastructure.database.repositories.trade_proposal_repository import (
    TradeProposalRepository,
)


class StrategyProposalService:
    def __init__(
        self,
        *,
        session: Session,
        minimum_confidence: float,
        maximum_buy_equity_fraction: float,
        maximum_sell_position_fraction: float,
        minimum_order_notional: float,
        maximum_quote_age_seconds: int,
        quote_interval: BarInterval,
        synthetic_spread_bps: float,
    ) -> None:
        self._account_repository = PaperAccountRepository(session)

        self._instrument_repository = InstrumentRepository(session)

        self._position_repository = PaperPositionRepository(session)

        self._proposal_repository = TradeProposalRepository(session)

        self._audit_repository = ExecutionAuditRepository(session)

        self._portfolio_service = PortfolioService(session=session)

        self._quote_service = MarketQuoteService(
            session=session,
            maximum_quote_age_seconds=(maximum_quote_age_seconds),
            quote_interval=(quote_interval),
            synthetic_spread_bps=(synthetic_spread_bps),
        )

        self._minimum_confidence = minimum_confidence

        self._maximum_buy_equity_fraction = maximum_buy_equity_fraction

        self._maximum_sell_position_fraction = maximum_sell_position_fraction

        self._minimum_order_notional = minimum_order_notional

    def create(
        self,
        *,
        account_id: UUID,
        symbol: str,
        side: OrderSide,
        confidence: float,
        source_model_id: UUID | None,
        source_prediction_id: UUID | None,
    ):
        validate_confidence(confidence)

        account = self._account_repository.get_by_id(account_id)

        if account is None:
            raise LookupError(f"Paper account not found: {account_id}")

        normalized_symbol = symbol.strip().upper()

        instrument = self._instrument_repository.get_model_by_symbol(normalized_symbol)

        if instrument is None:
            raise LookupError(f"Instrument not found: {normalized_symbol}")

        quote = self._quote_service.get_quote(symbol=instrument.symbol)

        reference_price = get_executable_reference_price(
            quote=quote,
            side=side,
        )

        portfolio = self._portfolio_service.summarize(
            account_id=account.id,
            prices={instrument.symbol: quote.midpoint},
        )

        position = self._position_repository.get(
            account_id=account.id,
            instrument_id=(instrument.id),
        )

        if side == OrderSide.BUY:
            sizing = calculate_buy_size(
                account_equity=(portfolio["equity"]),
                reference_price=(reference_price),
                confidence=confidence,
                minimum_confidence=(self._minimum_confidence),
                maximum_equity_fraction=(self._maximum_buy_equity_fraction),
            )

        else:
            current_quantity = 0.0

            if position is not None:
                current_quantity = max(
                    position.quantity,
                    0.0,
                )

            sizing = calculate_sell_size(
                current_position_quantity=(current_quantity),
                reference_price=(reference_price),
                confidence=confidence,
                minimum_confidence=(self._minimum_confidence),
                maximum_position_fraction=(self._maximum_sell_position_fraction),
            )

        rejection_reason: str | None = None

        if confidence < self._minimum_confidence:
            rejection_reason = "Signal confidence is below the strategy minimum."

        elif sizing.quantity <= 0:
            if side == OrderSide.SELL:
                rejection_reason = "Sell proposal requires an existing long position."
            else:
                rejection_reason = "Strategy sizing produced zero quantity."

        elif sizing.notional < self._minimum_order_notional:
            rejection_reason = "Proposed order notional is below the configured minimum."

        if rejection_reason is None:
            status = TradeProposalStatus.PENDING_APPROVAL
        else:
            status = TradeProposalStatus.REJECTED

        proposal = self._proposal_repository.create(
            account_id=account.id,
            instrument_id=(instrument.id),
            source_model_id=(source_model_id),
            source_prediction_id=(source_prediction_id),
            symbol=instrument.symbol,
            side=side.value,
            confidence=confidence,
            quantity=sizing.quantity,
            proposed_notional=(sizing.notional),
            allocation_fraction=(sizing.allocation_fraction),
            reference_price=(reference_price),
            reference_price_timestamp=(quote.timestamp),
            reference_price_provider=(quote.provider),
            status=status,
            rejection_reason=(rejection_reason),
        )

        self._audit_repository.create(
            account_id=account.id,
            event_type=("trade_proposal_created"),
            message=("Strategy trade proposal was created."),
            event_data={
                "proposal_id": (str(proposal.id)),
                "symbol": (proposal.symbol),
                "side": proposal.side,
                "confidence": confidence,
                "quantity": (proposal.quantity),
                "status": (proposal.status),
            },
        )

        return proposal
