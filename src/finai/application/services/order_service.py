from uuid import UUID

from sqlalchemy.orm import Session

from finai.application.services.paper_execution_service import (
    PaperExecutionService,
)
from finai.application.services.portfolio_service import (
    PortfolioService,
)
from finai.application.services.pre_trade_risk_service import (
    PreTradeRiskService,
)
from finai.domain.execution.enums import (
    OrderSide,
    OrderType,
    TimeInForce,
)
from finai.domain.execution.validation import (
    validate_order_request,
)
from finai.domain.portfolio.risk_limits import (
    PortfolioRiskLimits,
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
    ) -> None:
        self._instrument_repository = InstrumentRepository(session)

        self._account_repository = PaperAccountRepository(session)

        self._order_repository = OrderRepository(session)

        self._position_repository = PaperPositionRepository(session)

        self._portfolio_service = PortfolioService(session=session)

        self._risk_service = PreTradeRiskService()

        self._execution_service = PaperExecutionService(
            session=session,
            commission_bps=(commission_bps),
            slippage_bps=(slippage_bps),
        )

        self._risk_limits = risk_limits

    def submit(
        self,
        *,
        account_id: UUID,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        reference_price: float,
        limit_price: float | None,
        time_in_force: TimeInForce,
    ):
        validate_order_request(
            side=side,
            order_type=order_type,
            quantity=quantity,
            limit_price=limit_price,
        )

        account = self._account_repository.get_by_id(account_id)

        if account is None:
            raise LookupError(f"Paper account not found: {account_id}")

        instrument = self._instrument_repository.get_model_by_symbol(symbol.strip().upper())

        if instrument is None:
            raise LookupError(f"Instrument not found: {symbol}")

        order = self._order_repository.create(
            account_id=account.id,
            instrument_id=instrument.id,
            symbol=instrument.symbol,
            side=side.value,
            order_type=order_type.value,
            quantity=quantity,
            limit_price=limit_price,
            time_in_force=(time_in_force.value),
        )

        portfolio = self._portfolio_service.summarize(
            account_id=account.id,
            prices={instrument.symbol: reference_price},
        )

        position = self._position_repository.get(
            account_id=account.id,
            instrument_id=instrument.id,
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
            return self._order_repository.mark_rejected(
                order,
                reason=(risk_decision.reason or "Risk rejected order."),
            )

        self._execution_service.execute(
            order=order,
            reference_price=reference_price,
        )

        return self._order_repository.get_by_id(order.id)
