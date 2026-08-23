from sqlalchemy.orm import Session

from finai.application.services.alpaca_order_execution_service import (
    AlpacaOrderExecutionService,
)
from finai.infrastructure.database.repositories.order_repository import (
    OrderRepository,
)
from finai.infrastructure.execution.alpaca_broker import (
    AlpacaPaperBroker,
)


class AlpacaTradeUpdateService:
    def __init__(
        self,
        *,
        session: Session,
        broker: AlpacaPaperBroker,
        execution_service: (
            AlpacaOrderExecutionService
        ),
    ) -> None:
        self._repository = (
            OrderRepository(
                session
            )
        )

        self._broker = broker

        self._execution_service = (
            execution_service
        )

    def process(
        self,
        *,
        message: dict,
    ) -> bool:
        if (
            message.get("stream")
            != "trade_updates"
        ):
            return False

        data = message.get(
            "data"
        )

        if not isinstance(
            data,
            dict,
        ):
            return False

        event = str(
            data.get(
                "event",
                "unknown",
            )
        )

        order_payload = data.get(
            "order"
        )

        if not isinstance(
            order_payload,
            dict,
        ):
            return False

        broker_order_id = str(
            order_payload.get(
                "id",
                "",
            )
        ).strip()

        if not broker_order_id:
            return False

        order = (
            self._repository
            .get_by_broker_order_id(
                broker_order_id
            )
        )

        if order is None:
            return False

        if (
            order.broker_name
            != self._broker.name
        ):
            return False

        snapshot = (
            self._broker
            .snapshot_from_response(
                order_payload
            )
        )

        self._execution_service.sync_from_snapshot(
            order=order,
            snapshot=snapshot,
            source=(
                f"trade_updates:{event}"
            ),
        )

        return True