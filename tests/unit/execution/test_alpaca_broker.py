from finai.domain.execution.enums import (
    OrderStatus,
)
from finai.infrastructure.execution.alpaca_broker import (
    AlpacaPaperBroker,
)


def test_filled_status() -> None:
    assert (
        AlpacaPaperBroker._map_status(
            "filled"
        )
        == OrderStatus.FILLED
    )


def test_partial_status() -> None:
    assert (
        AlpacaPaperBroker._map_status(
            "partially_filled"
        )
        == (
            OrderStatus
            .PARTIALLY_FILLED
        )
    )


def test_cancel_status() -> None:
    assert (
        AlpacaPaperBroker._map_status(
            "canceled"
        )
        == OrderStatus.CANCELLED
    )


def test_expired_status() -> None:
    assert (
        AlpacaPaperBroker._map_status(
            "expired"
        )
        == OrderStatus.CANCELLED
    )


def test_rejected_status() -> None:
    assert (
        AlpacaPaperBroker._map_status(
            "rejected"
        )
        == OrderStatus.REJECTED
    )


def test_new_is_accepted() -> None:
    assert (
        AlpacaPaperBroker._map_status(
            "new"
        )
        == OrderStatus.ACCEPTED
    )


def test_pending_new_is_accepted() -> None:
    assert (
        AlpacaPaperBroker._map_status(
            "pending_new"
        )
        == OrderStatus.ACCEPTED
    )