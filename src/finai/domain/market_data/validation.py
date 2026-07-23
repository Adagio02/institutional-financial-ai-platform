from finai.domain.market_data.entities import Instrument, MarketBar


def normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()

    if not normalized:
        raise ValueError("Symbol cannot be empty.")

    if len(normalized) > 32:
        raise ValueError("Symbol cannot exceed 32 characters.")

    return normalized


def validate_instrument(instrument: Instrument) -> None:
    normalize_symbol(instrument.symbol)

    if not instrument.name.strip():
        raise ValueError("Instrument name cannot be empty.")

    if not instrument.exchange.strip():
        raise ValueError("Exchange cannot be empty.")

    if len(instrument.currency.strip()) != 3:
        raise ValueError("Currency must use a three-letter code.")


def validate_market_bar(bar: MarketBar) -> None:
    normalize_symbol(bar.symbol)

    if bar.open_price <= 0:
        raise ValueError("Open price must be greater than zero.")

    if bar.high_price <= 0:
        raise ValueError("High price must be greater than zero.")

    if bar.low_price <= 0:
        raise ValueError("Low price must be greater than zero.")

    if bar.close_price <= 0:
        raise ValueError("Close price must be greater than zero.")

    if bar.high_price < bar.low_price:
        raise ValueError("High price cannot be lower than low price.")

    if bar.high_price < max(bar.open_price, bar.close_price):
        raise ValueError("High price cannot be lower than the open or close price.")

    if bar.low_price > min(bar.open_price, bar.close_price):
        raise ValueError("Low price cannot be higher than the open or close price.")

    if bar.volume < 0:
        raise ValueError("Volume cannot be negative.")

    if bar.timestamp.tzinfo is None:
        raise ValueError("Market-bar timestamp must be timezone-aware.")
