from uuid import UUID

from sqlalchemy.orm import Session

from finai.application.services.broker_execution_service import (
    BrokerExecutionService,
)
from finai.application.services.market_quote_service import (
    MarketQuoteService,
)
from finai.domain.execution.enums import (
    OrderSide,
    OrderStatus,
)
from finai.domain.market_data.enums import (
    BarInterval,
)
from finai.domain.market_data.execution_quote import (
    get_executable_reference_price,
)
from finai.infrastructure.database.repositories.order_repository import (
    OrderRepository,
)
from finai.infrastructure.execution.sandbox_broker import (
    SandboxBroker,
)


class OrderSyncService:
    def __init__(
        self,
        *,
        session: Session,
        commission_bps: float,
        slippage_bps: float,
        maximum_quote_age_seconds: int,
        quote_interval: BarInterval,
        synthetic_spread_bps: float,
    ) -> None:
        self._order_repository = OrderRepository(session)

        self._quote_service = MarketQuoteService(
            session=session,
            maximum_quote_age_seconds=(maximum_quote_age_seconds),
            quote_interval=quote_interval,
            synthetic_spread_bps=(synthetic_spread_bps),
        )

        broker = SandboxBroker(
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
            partial_fill_enabled=False,
            initial_fill_fraction=1.0,
        )

        self._execution_service = BrokerExecutionService(
            session=session,
            broker=broker,
        )

    def sync(
        self,
        *,
        order_id: UUID,
    ):
        order = self._order_repository.get_by_id(order_id)

        if order is None:
            raise LookupError(f"Order not found: {order_id}")

        if order.status not in {
            OrderStatus.ACCEPTED.value,
            (OrderStatus.PARTIALLY_FILLED.value),
        }:
            return order

        if order.remaining_quantity <= 0:
            return order

        quote = self._quote_service.get_quote(symbol=order.symbol)

        reference_price = get_executable_reference_price(
            quote=quote,
            side=OrderSide(order.side),
        )

        return self._execution_service.execute(
            order=order,
            reference_price=(reference_price),
        )
