from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PositionAccountingResult:
    quantity: float
    average_price: float
    realized_pnl_delta: float


def apply_fill_to_position(
    *,
    current_quantity: float,
    current_average_price: float,
    fill_quantity: float,
    fill_price: float,
) -> PositionAccountingResult:
    if fill_quantity == 0:
        raise ValueError("fill_quantity cannot be zero.")

    if fill_price <= 0:
        raise ValueError("fill_price must be positive.")

    if current_quantity != 0 and current_average_price <= 0:
        raise ValueError("An open position must have a positive average price.")

    new_quantity = current_quantity + fill_quantity

    if current_quantity == 0:
        return PositionAccountingResult(
            quantity=new_quantity,
            average_price=fill_price,
            realized_pnl_delta=0.0,
        )

    same_direction = (current_quantity > 0 and fill_quantity > 0) or (
        current_quantity < 0 and fill_quantity < 0
    )

    if same_direction:
        existing_notional = abs(current_quantity) * current_average_price

        added_notional = abs(fill_quantity) * fill_price

        total_quantity = abs(current_quantity) + abs(fill_quantity)

        average_price = (existing_notional + added_notional) / total_quantity

        return PositionAccountingResult(
            quantity=new_quantity,
            average_price=average_price,
            realized_pnl_delta=0.0,
        )

    closed_quantity = min(
        abs(current_quantity),
        abs(fill_quantity),
    )

    if current_quantity > 0:
        realized_pnl_delta = (fill_price - current_average_price) * closed_quantity

    else:
        realized_pnl_delta = (current_average_price - fill_price) * closed_quantity

    if new_quantity == 0:
        new_average_price = 0.0

    elif (current_quantity > 0 and new_quantity > 0) or (current_quantity < 0 and new_quantity < 0):
        new_average_price = current_average_price

    else:
        new_average_price = fill_price

    return PositionAccountingResult(
        quantity=new_quantity,
        average_price=new_average_price,
        realized_pnl_delta=realized_pnl_delta,
    )
