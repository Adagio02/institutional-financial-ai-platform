from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class MarketQuote:
    symbol: str
    price: float
    timestamp: datetime
    provider: str