from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class MarketQuote:
    symbol: str

    bid: float
    ask: float
    last: float

    timestamp: datetime
    provider: str

    @property
    def midpoint(self) -> float:
        return (self.bid + self.ask) / 2.0
