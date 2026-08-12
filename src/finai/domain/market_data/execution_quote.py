from finai.domain.execution.enums import (
    OrderSide,
)
from finai.domain.market_data.quote import (
    MarketQuote,
)


def get_executable_reference_price(
    *,
    quote: MarketQuote,
    side: OrderSide,
) -> float:
    if quote.bid <= 0:
        raise ValueError("Market quote bid must be positive.")

    if quote.ask <= 0:
        raise ValueError("Market quote ask must be positive.")

    if quote.last <= 0:
        raise ValueError("Market quote last price must be positive.")

    if quote.ask < quote.bid:
        raise ValueError("Market quote ask cannot be lower than bid.")

    if side == OrderSide.BUY:
        return quote.ask

    if side == OrderSide.SELL:
        return quote.bid

    raise ValueError(f"Unsupported order side: {side}")
