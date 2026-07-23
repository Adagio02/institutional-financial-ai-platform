from datetime import datetime
from typing import Protocol

from finai.domain.market_data.entities import MarketBar
from finai.domain.market_data.enums import BarInterval


class MarketDataProvider(Protocol):
    @property
    def name(self) -> str:
        """Return the provider identifier."""

    def get_historical_bars(
        self,
        *,
        symbol: str,
        interval: BarInterval,
        start_time: datetime,
        end_time: datetime,
    ) -> list[MarketBar]:
        """Retrieve historical market bars."""
