from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StrategySizingResult:
    quantity: float
    notional: float
    allocation_fraction: float


def validate_confidence(
    confidence: float,
) -> None:
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between zero and one.")


def calculate_buy_size(
    *,
    account_equity: float,
    reference_price: float,
    confidence: float,
    minimum_confidence: float,
    maximum_equity_fraction: float,
) -> StrategySizingResult:
    validate_confidence(confidence)

    if account_equity <= 0:
        raise ValueError("account_equity must be positive.")

    if reference_price <= 0:
        raise ValueError("reference_price must be positive.")

    if not 0 <= minimum_confidence <= 1:
        raise ValueError("minimum_confidence must be between zero and one.")

    if not 0 < maximum_equity_fraction <= 1:
        raise ValueError("maximum_equity_fraction must be greater than zero and at most one.")

    if confidence < minimum_confidence:
        return StrategySizingResult(
            quantity=0.0,
            notional=0.0,
            allocation_fraction=0.0,
        )

    allocation_fraction = maximum_equity_fraction * confidence

    notional = account_equity * allocation_fraction

    quantity = notional / reference_price

    return StrategySizingResult(
        quantity=quantity,
        notional=notional,
        allocation_fraction=(allocation_fraction),
    )


def calculate_sell_size(
    *,
    current_position_quantity: float,
    reference_price: float,
    confidence: float,
    minimum_confidence: float,
    maximum_position_fraction: float,
) -> StrategySizingResult:
    validate_confidence(confidence)

    if reference_price <= 0:
        raise ValueError("reference_price must be positive.")

    if current_position_quantity <= 0:
        return StrategySizingResult(
            quantity=0.0,
            notional=0.0,
            allocation_fraction=0.0,
        )

    if not 0 <= minimum_confidence <= 1:
        raise ValueError("minimum_confidence must be between zero and one.")

    if not 0 < maximum_position_fraction <= 1:
        raise ValueError("maximum_position_fraction must be greater than zero and at most one.")

    if confidence < minimum_confidence:
        return StrategySizingResult(
            quantity=0.0,
            notional=0.0,
            allocation_fraction=0.0,
        )

    allocation_fraction = maximum_position_fraction * confidence

    quantity = current_position_quantity * allocation_fraction

    notional = quantity * reference_price

    return StrategySizingResult(
        quantity=quantity,
        notional=notional,
        allocation_fraction=(allocation_fraction),
    )
