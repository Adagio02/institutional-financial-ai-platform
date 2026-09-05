def calculate_position_notional(
    *,
    portfolio_equity: float,
    position_size_fraction: float,
) -> float:
    if portfolio_equity <= 0:
        return 0.0

    return portfolio_equity * position_size_fraction


def calculate_quantity(
    *,
    position_notional: float,
    price: float,
) -> float:
    if price <= 0:
        raise ValueError("Execution price must be positive.")

    return position_notional / price
