from datetime import (
    UTC,
    datetime,
    timedelta,
)

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


class PersistedQuoteProvider:
    def __init__(
        self,
        *,
        session: Session,
        interval: BarInterval,
        maximum_age_seconds: int,
        synthetic_spread_bps: float,
    ) -> None:
        if maximum_age_seconds <= 0:
            raise ValueError("maximum_age_seconds must be positive.")

        if synthetic_spread_bps < 0:
            raise ValueError("synthetic_spread_bps cannot be negative.")

        self._instrument_repository = InstrumentRepository(session)

        self._market_bar_repository = MarketBarRepository(session)

        self._interval = interval

        self._maximum_age_seconds = maximum_age_seconds

        self._synthetic_spread_bps = synthetic_spread_bps

    def get_quote(
        self,
        *,
        symbol: str,
    ) -> MarketQuote:
        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("Symbol cannot be empty.")

        instrument = self._instrument_repository.get_model_by_symbol(normalized_symbol)

        if instrument is None:
            raise LookupError(f"Instrument not found: {normalized_symbol}")

        bar = self._market_bar_repository.get_latest_bar(
            instrument_id=(instrument.id),
            interval=self._interval,
        )

        if bar is None:
            raise LookupError(f"No market data is available for {normalized_symbol}.")

        timestamp = bar.timestamp

        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)

        maximum_age = timedelta(seconds=(self._maximum_age_seconds))

        if datetime.now(UTC) - timestamp > maximum_age:
            raise ValueError(
                "Latest market quote is stale. "
                f"symbol={normalized_symbol}, "
                "quote_timestamp="
                f"{timestamp.isoformat()}"
            )

        last = float(bar.close_price)

        if last <= 0:
            raise ValueError("Latest market price must be positive.")

        half_spread = self._synthetic_spread_bps / 20_000.0

        bid = last * (1.0 - half_spread)

        ask = last * (1.0 + half_spread)

        return MarketQuote(
            symbol=normalized_symbol,
            bid=bid,
            ask=ask,
            last=last,
            timestamp=timestamp,
            provider=bar.provider,
        )
