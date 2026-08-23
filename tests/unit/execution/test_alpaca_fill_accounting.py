import pytest


def calculate_delta_fill_price(
    *,
    previous_quantity: float,
    previous_average_price: float,
    new_quantity: float,
    new_average_price: float,
) -> tuple[float, float]:
    delta_quantity = (
        new_quantity
        - previous_quantity
    )

    new_notional = (
        new_quantity
        * new_average_price
    )

    previous_notional = (
        previous_quantity
        * previous_average_price
    )

    delta_notional = (
        new_notional
        - previous_notional
    )

    return (
        delta_quantity,
        delta_notional
        / delta_quantity,
    )


def test_first_partial_fill() -> None:
    quantity, price = (
        calculate_delta_fill_price(
            previous_quantity=0.0,
            previous_average_price=0.0,
            new_quantity=2.0,
            new_average_price=100.0,
        )
    )

    assert quantity == pytest.approx(
        2.0
    )

    assert price == pytest.approx(
        100.0
    )


def test_second_partial_fill_is_delta() -> None:
    quantity, price = (
        calculate_delta_fill_price(
            previous_quantity=2.0,
            previous_average_price=100.0,
            new_quantity=6.0,
            new_average_price=102.0,
        )
    )

    assert quantity == pytest.approx(
        4.0
    )

    assert price == pytest.approx(
        103.0
    )


def test_final_fill_is_only_remaining_delta() -> None:
    quantity, price = (
        calculate_delta_fill_price(
            previous_quantity=6.0,
            previous_average_price=102.0,
            new_quantity=10.0,
            new_average_price=103.0,
        )
    )

    assert quantity == pytest.approx(
        4.0
    )

    assert price == pytest.approx(
        104.5
    )