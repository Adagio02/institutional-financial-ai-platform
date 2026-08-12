from sqlalchemy.orm import Session

from finai.domain.market_data.enums import (
    BarInterval,
)
from finai.domain.market_data.quote import (
    MarketQuote,
)
from finai.infrastructure.market_data.persisted_quote_provider import (
    PersistedQuoteProvider,
)


class MarketQuoteService:
    def __init__(
        self,
        *,
        session: Session,
        maximum_quote_age_seconds: int,
        quote_interval: BarInterval,
        synthetic_spread_bps: float,
    ) -> None:
        self._provider = PersistedQuoteProvider(
            session=session,
            interval=quote_interval,
            maximum_age_seconds=(maximum_quote_age_seconds),
            synthetic_spread_bps=(synthetic_spread_bps),
        )

    def get_quote(
        self,
        *,
        symbol: str,
    ) -> MarketQuote:
        return self._provider.get_quote(symbol=symbol)
