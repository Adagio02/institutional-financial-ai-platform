import pytest

from finai.domain.execution.alpaca_idempotency_guard import (
    AlpacaIdempotencyGuard,
)


def make_guard(
) -> AlpacaIdempotencyGuard:
    return AlpacaIdempotencyGuard(
        require_order_match=True
    )


def make_order(
    *,
    client_order_id: str = "v27-test-123",
    symbol: str = "AAPL",
    side: str = "buy",
    order_type: str = "market",
    quantity: str = "1",
    time_in_force: str = "day",
) -> dict:
    return {
        "id": (
            "11111111-1111-1111-"
            "1111-111111111111"
        ),
        "client_order_id": (
            client_order_id
        ),
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "qty": quantity,
        "time_in_force": (
            time_in_force
        ),
        "status": "accepted",
    }


def test_exact_existing_order_matches() -> None:
    result = (
        make_guard()
        .validate_existing_order(
            existing_order=(
                make_order()
            ),
            client_order_id=(
                "v27-test-123"
            ),
            symbol="AAPL",
            side="buy",
            order_type="market",
            quantity=1.0,
            time_in_force="day",
        )
    )

    assert (
        result.client_order_id
        == "v27-test-123"
    )

    assert result.symbol == "AAPL"


def test_symbol_mismatch_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="symbol does not match",
    ):
        (
            make_guard()
            .validate_existing_order(
                existing_order=(
                    make_order(
                        symbol="MSFT"
                    )
                ),
                client_order_id=(
                    "v27-test-123"
                ),
                symbol="AAPL",
                side="buy",
                order_type="market",
                quantity=1.0,
                time_in_force="day",
            )
        )


def test_side_mismatch_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="side does not match",
    ):
        (
            make_guard()
            .validate_existing_order(
                existing_order=(
                    make_order(
                        side="sell"
                    )
                ),
                client_order_id=(
                    "v27-test-123"
                ),
                symbol="AAPL",
                side="buy",
                order_type="market",
                quantity=1.0,
                time_in_force="day",
            )
        )


def test_quantity_mismatch_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="quantity does not match",
    ):
        (
            make_guard()
            .validate_existing_order(
                existing_order=(
                    make_order(
                        quantity="2"
                    )
                ),
                client_order_id=(
                    "v27-test-123"
                ),
                symbol="AAPL",
                side="buy",
                order_type="market",
                quantity=1.0,
                time_in_force="day",
            )
        )


def test_type_mismatch_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="type does not match",
    ):
        (
            make_guard()
            .validate_existing_order(
                existing_order=(
                    make_order(
                        order_type="limit"
                    )
                ),
                client_order_id=(
                    "v27-test-123"
                ),
                symbol="AAPL",
                side="buy",
                order_type="market",
                quantity=1.0,
                time_in_force="day",
            )
        )


def test_time_in_force_mismatch_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="time_in_force",
    ):
        (
            make_guard()
            .validate_existing_order(
                existing_order=(
                    make_order(
                        time_in_force="gtc"
                    )
                ),
                client_order_id=(
                    "v27-test-123"
                ),
                symbol="AAPL",
                side="buy",
                order_type="market",
                quantity=1.0,
                time_in_force="day",
            )
        )


def test_client_order_id_limit() -> None:
    with pytest.raises(
        ValueError,
        match="128",
    ):
        (
            make_guard()
            .validate_client_order_id(
                "x" * 129
            )
        )


def test_client_order_id_128_is_allowed() -> None:
    value = (
        make_guard()
        .validate_client_order_id(
            "x" * 128
        )
    )

    assert len(value) == 128