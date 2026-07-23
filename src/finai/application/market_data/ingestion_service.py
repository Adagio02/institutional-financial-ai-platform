from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

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
        session: Session,
        provider: MarketDataProvider,
        maximum_bars: int = 10_000,
    ) -> None:
        self._instrument_repository = InstrumentRepository(session)
        self._market_bar_repository = MarketBarRepository(session)
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
        if start_time.tzinfo is None or end_time.tzinfo is None:
            raise ValueError("Start and end times must be timezone-aware.")

        if start_time >= end_time:
            raise ValueError("Start time must be earlier than end time.")

        instrument_model = self._instrument_repository.get_model_by_symbol(symbol)

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
