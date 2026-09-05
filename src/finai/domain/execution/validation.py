from finai.domain.execution.enums import (
    OrderSide,
    OrderType,
)


def validate_order_request(
    *,
    side: OrderSide,
    order_type: OrderType,
    quantity: float,
    limit_price: float | None,
) -> None:
    if quantity <= 0:
        raise ValueError("Order quantity must be greater than zero.")

    if order_type == OrderType.LIMIT and limit_price is None:
        raise ValueError("Limit orders require limit_price.")

    if limit_price is not None and limit_price <= 0:
        raise ValueError("limit_price must be greater than zero.")

    if side not in {
        OrderSide.BUY,
        OrderSide.SELL,
    }:
        raise ValueError("Unsupported order side.")
