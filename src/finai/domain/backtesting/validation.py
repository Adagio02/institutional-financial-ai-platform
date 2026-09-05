def validate_backtest_configuration(
    *,
    initial_capital: float,
    long_threshold: float,
    short_threshold: float,
    position_size_fraction: float,
    commission_bps: float,
    slippage_bps: float,
) -> None:
    if initial_capital <= 0:
        raise ValueError("initial_capital must be greater than zero.")

    if not 0 < position_size_fraction <= 1:
        raise ValueError(
            "position_size_fraction must be greater than zero and no greater than one."
        )

    if commission_bps < 0:
        raise ValueError("commission_bps cannot be negative.")

    if slippage_bps < 0:
        raise ValueError("slippage_bps cannot be negative.")

    if short_threshold >= long_threshold:
        raise ValueError("short_threshold must be lower than long_threshold.")
