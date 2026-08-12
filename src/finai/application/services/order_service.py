from uuid import UUID

from sqlalchemy.orm import Session

from finai.application.services.market_quote_service import (
    MarketQuoteService,
)
from finai.application.services.paper_execution_service import (
    PaperExecutionService,
)
from finai.application.services.portfolio_service import (
    PortfolioService,
)
from finai.application.services.pre_trade_risk_service import (
    PreTradeRiskService,
)
from finai.application.services.trading_control_service import (
    TradingControlService,
)
from finai.domain.execution.enums import (
    OrderSide,
    OrderType,
    TimeInForce,
)
from finai.domain.execution.validation import (
    validate_order_request,
)
from finai.domain.market_data.enums import (
    BarInterval,
)
from finai.domain.portfolio.risk_limits import (
    PortfolioRiskLimits,
)
from finai.infrastructure.database.repositories.execution_audit_repository import (
    ExecutionAuditRepository,
)
from finai.infrastructure.database.repositories.instrument_repository import (
    InstrumentRepository,
)
from finai.infrastructure.database.repositories.order_repository import (
    OrderRepository,
)
from finai.infrastructure.database.repositories.paper_account_repository import (
    PaperAccountRepository,
)
from finai.infrastructure.database.repositories.paper_position_repository import (
    PaperPositionRepository,
)


class OrderService:
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
    ) -> None:
        self._instrument_repository = InstrumentRepository(session)

        self._account_repository = PaperAccountRepository(session)

        self._order_repository = OrderRepository(session)

        self._position_repository = PaperPositionRepository(session)

        self._audit_repository = ExecutionAuditRepository(session)

        self._portfolio_service = PortfolioService(session=session)

        self._risk_service = PreTradeRiskService()

        self._trading_control_service = TradingControlService(session=session)

        self._execution_service = PaperExecutionService(
            session=session,
            commission_bps=(commission_bps),
            slippage_bps=(slippage_bps),
        )

        self._market_quote_service = MarketQuoteService(
            session=session,
            maximum_quote_age_seconds=(maximum_quote_age_seconds),
            quote_interval=(quote_interval),
        )

        self._risk_limits = risk_limits

        self._maximum_daily_loss = maximum_daily_loss

    def submit(
        self,
        *,
        account_id: UUID,
        client_order_id: str | None,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        limit_price: float | None,
        time_in_force: TimeInForce,
    ):
        self._trading_control_service.assert_trading_allowed()

        validate_order_request(
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
        )

        account = self._account_repository.get_by_id(account_id)

        if account is None:
            raise LookupError(f"Paper account not found: {account_id}")

        if client_order_id is not None:
            normalized_client_order_id = client_order_id.strip()

            if not normalized_client_order_id:
                raise ValueError("client_order_id cannot be blank.")

            existing_order = self._order_repository.get_by_client_order_id(
                account_id=account.id,
                client_order_id=(normalized_client_order_id),
            )

            if existing_order is not None:
                return existing_order

        else:
            normalized_client_order_id = None

        if account.realized_pnl <= -abs(self._maximum_daily_loss):
            raise ValueError("Account has reached the maximum daily loss limit.")

        normalized_symbol = symbol.strip().upper()

        instrument = self._instrument_repository.get_model_by_symbol(normalized_symbol)

        if instrument is None:
            raise LookupError(f"Instrument not found: {normalized_symbol}")

        quote = self._market_quote_service.get_quote(symbol=instrument.symbol)

        reference_price = quote.price

        order = self._order_repository.create(
            account_id=account.id,
            instrument_id=(instrument.id),
            client_order_id=(normalized_client_order_id),
            symbol=instrument.symbol,
            side=side.value,
            order_type=(order_type.value),
            quantity=quantity,
            limit_price=limit_price,
            time_in_force=(time_in_force.value),
            reference_price=(reference_price),
            reference_price_timestamp=(quote.timestamp),
            reference_price_provider=(quote.provider),
        )

        self._audit_repository.create(
            account_id=account.id,
            order_id=order.id,
            event_type="order_created",
            message=("Paper order was created."),
            event_data={
                "symbol": (instrument.symbol),
                "side": side.value,
                "quantity": quantity,
                "reference_price": (reference_price),
                "provider": (quote.provider),
            },
        )

        portfolio = self._portfolio_service.summarize(
            account_id=account.id,
            prices={instrument.symbol: (reference_price)},
        )

        position = self._position_repository.get(
            account_id=account.id,
            instrument_id=(instrument.id),
        )

        current_position_notional = 0.0

        if position is not None:
            current_position_notional = position.quantity * reference_price

        signed_notional = quantity * reference_price

        if side == OrderSide.SELL:
            signed_notional *= -1

        risk_decision = self._risk_service.evaluate(
            order_notional=(signed_notional),
            current_position_notional=(current_position_notional),
            current_gross_exposure=(portfolio["gross_exposure"]),
            account_equity=(portfolio["equity"]),
            account_cash=(account.cash),
            is_buy=(side == OrderSide.BUY),
            limits=(self._risk_limits),
        )

        if not risk_decision.approved:
            rejected_order = self._order_repository.mark_rejected(
                order,
                reason=(risk_decision.reason or ("Risk rejected order.")),
            )

            self._audit_repository.create(
                account_id=account.id,
                order_id=order.id,
                event_type=("order_rejected"),
                message=("Paper order was rejected by risk."),
                event_data={"reason": (rejected_order.rejection_reason)},
            )

            return rejected_order

        self._execution_service.execute(
            order=order,
            reference_price=reference_price,
        )

        return self._order_repository.get_by_id(order.id)
