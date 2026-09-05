from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from finai.domain.market_data.enums import AssetClass, BarInterval


@dataclass(frozen=True, slots=True)
class Instrument:
    symbol: str
    name: str
    asset_class: AssetClass
    exchange: str
    currency: str = "USD"
    active: bool = True
    instrument_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class MarketBar:
    symbol: str
    interval: BarInterval
    timestamp: datetime
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: Decimal
    provider: str
