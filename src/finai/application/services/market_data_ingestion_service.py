from dataclasses import dataclass
from datetime import datetime

from finai.core.exceptions import ResourceNotFoundError
from finai.domain.market_data.enums import BarInterval
from finai.infrastructure.database.repositories.instrument_repository import (
    InstrumentRepository,
)
from finai.infrastructure.database.repositories.market_bar_repository import (
    MarketBarRepository,
)
from finai.infrastructure.market_data.provider import MarketDataProvider


@dataclass(frozen=True, slots=True)
class IngestionResult:
    symbol: str
    interval: BarInterval
    provider: str
    bars_received: int
    bars_persisted: int
    start_time: datetime
    end_time: datetime


class MarketDataIngestionService:
    def __init__(
        self,
        *,
        instrument_repository: InstrumentRepository,
        market_bar_repository: MarketBarRepository,
        provider: MarketDataProvider,
        maximum_bars: int = 10_000,
    ) -> None:
        self._instrument_repository = instrument_repository
        self._market_bar_repository = market_bar_repository
        self._provider = provider
        self._maximum_bars = maximum_bars

    def ingest(
        self,
        *,
        symbol: str,
        interval: BarInterval,
        start_time: datetime,
        end_time: datetime,
    ) -> IngestionResult:
        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            raise ValueError("Symbol cannot be empty.")

        if start_time.tzinfo is None or end_time.tzinfo is None:
            raise ValueError("Start and end times must be timezone-aware.")

        if start_time >= end_time:
            raise ValueError("Start time must be earlier than end time.")

        instrument_model = self._instrument_repository.get_model_by_symbol(normalized_symbol)

        if instrument_model is None:
            raise ResourceNotFoundError(f"Instrument not found: {normalized_symbol}")

        bars = self._provider.get_historical_bars(
            symbol=instrument_model.symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
        )

        if len(bars) > self._maximum_bars:
            raise ValueError("Provider returned more bars than the configured limit.")

        persisted_count = self._market_bar_repository.upsert_many(
            instrument=instrument_model,
            bars=bars,
        )

        return IngestionResult(
            symbol=instrument_model.symbol,
            interval=interval,
            provider=self._provider.name,
            bars_received=len(bars),
            bars_persisted=persisted_count,
            start_time=start_time,
            end_time=end_time,
        )
