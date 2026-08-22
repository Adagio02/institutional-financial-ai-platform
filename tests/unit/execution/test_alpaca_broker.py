from finai.domain.execution.enums import (
    OrderStatus,
)
from finai.infrastructure.execution.alpaca_broker import (
    AlpacaPaperBroker,
)


def test_alpaca_filled_status() -> None:
    assert (
        AlpacaPaperBroker._map_status(
            "filled"
        )
        == OrderStatus.FILLED
    )


def test_alpaca_partial_status() -> None:
    assert (
        AlpacaPaperBroker._map_status(
            "partially_filled"
        )
        == (
            OrderStatus
            .PARTIALLY_FILLED
        )
    )


def test_alpaca_cancelled_status() -> None:
    assert (
        AlpacaPaperBroker._map_status(
            "canceled"
        )
        == OrderStatus.CANCELLED
    )


def test_alpaca_rejected_status() -> None:
    assert (
        AlpacaPaperBroker._map_status(
            "rejected"
        )
        == OrderStatus.REJECTED
    )


def test_unknown_status_is_accepted() -> None:
    assert (
        AlpacaPaperBroker._map_status(
            "new"
        )
        == OrderStatus.ACCEPTED
    )