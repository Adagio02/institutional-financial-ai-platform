from finai.domain.execution.enums import (
    OrderStatus,
)
from finai.infrastructure.execution.alpaca_broker import (
    AlpacaPaperBroker,
)


def test_trade_update_fill_snapshot() -> None:
    snapshot = (
        AlpacaPaperBroker
        .snapshot_from_response(
            {
                "id": (
                    "broker-order-1"
                ),
                "client_order_id": (
                    "finai-1"
                ),
                "symbol": "AAPL",
                "status": "filled",
                "qty": "1",
                "filled_qty": "1",
                "filled_avg_price": (
                    "250.50"
                ),
            }
        )
    )

    assert (
        snapshot.broker_order_id
        == "broker-order-1"
    )

    assert (
        snapshot.status
        == OrderStatus.FILLED
    )

    assert (
        snapshot.filled_quantity
        == 1.0
    )

    assert (
        snapshot.average_fill_price
        == 250.50
    )


def test_partial_fill_snapshot() -> None:
    snapshot = (
        AlpacaPaperBroker
        .snapshot_from_response(
            {
                "id": (
                    "broker-order-2"
                ),
                "symbol": "AAPL",
                "status": (
                    "partially_filled"
                ),
                "qty": "10",
                "filled_qty": "4",
                "filled_avg_price": (
                    "101.25"
                ),
            }
        )
    )

    assert (
        snapshot.status
        == (
            OrderStatus
            .PARTIALLY_FILLED
        )
    )

    assert (
        snapshot
        .requested_quantity
        == 10.0
    )

    assert (
        snapshot
        .filled_quantity
        == 4.0
    )