from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from finai.domain.market_data.enums import (
    BarInterval,
)
from finai.domain.market_data.quote import (
    MarketQuote,
)
from finai.infrastructure.database.repositories.instrument_repository import (
    InstrumentRepository,
)
from finai.infrastructure.database.repositories.market_bar_repository import (
    MarketBarRepository,
)


class MarketQuoteService:
    def __init__(
        self,
        *,
        session: Session,
        maximum_quote_age_seconds: int = 86_400,
        quote_interval: BarInterval = BarInterval.ONE_DAY,
    ) -> None:
        self._instrument_repository = InstrumentRepository(
            session
        )

        self._market_bar_repository = MarketBarRepository(
            session
        )

        self._maximum_quote_age_seconds = (
            maximum_quote_age_seconds
        )

        self._quote_interval = quote_interval

    def get_quote(
        self,
        *,
        symbol: str,
    ) -> MarketQuote:
        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError(
                "Symbol cannot be empty."
            )

        instrument = (
            self._instrument_repository
            .get_model_by_symbol(
                normalized_symbol
            )
        )

        if instrument is None:
            raise LookupError(
                f"Instrument not found: "
                f"{normalized_symbol}"
            )

        bar = (
            self._market_bar_repository
            .get_latest_bar(
                instrument_id=instrument.id,
                interval=self._quote_interval,
            )
        )

        if bar is None:
            raise LookupError(
                "No market data is available for "
                f"{normalized_symbol}."
            )

        price = float(
            bar.close_price
        )

        if price <= 0:
            raise ValueError(
                "Latest market price must be positive."
            )

        quote_timestamp = bar.timestamp

        if quote_timestamp.tzinfo is None:
            quote_timestamp = (
                quote_timestamp.replace(
                    tzinfo=UTC
                )
            )

        current_time = datetime.now(UTC)

        maximum_quote_age = timedelta(
            seconds=(
                self._maximum_quote_age_seconds
            )
        )

        quote_age = (
            current_time
            - quote_timestamp
        )

        if quote_age > maximum_quote_age:
            raise ValueError(
                "Latest market quote is stale. "
                f"symbol={normalized_symbol}, "
                f"quote_timestamp="
                f"{quote_timestamp.isoformat()}"
            )

        return MarketQuote(
            symbol=normalized_symbol,
            price=price,
            timestamp=quote_timestamp,
            provider=bar.provider,
        )