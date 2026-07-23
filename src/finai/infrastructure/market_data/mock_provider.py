import hashlib
import random
from datetime import datetime, timedelta
from decimal import Decimal

from finai.domain.market_data.entities import MarketBar
from finai.domain.market_data.enums import BarInterval
from finai.domain.market_data.validation import normalize_symbol


_INTERVAL_DELTAS: dict[BarInterval, timedelta] = {
    BarInterval.ONE_MINUTE: timedelta(minutes=1),
    BarInterval.FIVE_MINUTES: timedelta(minutes=5),
    BarInterval.FIFTEEN_MINUTES: timedelta(minutes=15),
    BarInterval.ONE_HOUR: timedelta(hours=1),
    BarInterval.ONE_DAY: timedelta(days=1),
}


class MockMarketDataProvider:
    @property
    def name(self) -> str:
        return "mock"

    def get_historical_bars(
        self,
        *,
        symbol: str,
        interval: BarInterval,
        start_time: datetime,
        end_time: datetime,
    ) -> list[MarketBar]:
        normalized_symbol = normalize_symbol(symbol)

        if start_time.tzinfo is None or end_time.tzinfo is None:
            raise ValueError("Start and end times must be timezone-aware.")

        if start_time >= end_time:
            raise ValueError("Start time must be earlier than end time.")

        seed_source = (
            f"{normalized_symbol}:{interval.value}:{start_time.isoformat()}:{end_time.isoformat()}"
        )

        seed = int(
            hashlib.sha256(seed_source.encode()).hexdigest()[:16],
            16,
        )

        random_generator = random.Random(seed)

        base_price = Decimal(str(50 + (seed % 450))).quantize(Decimal("0.0001"))

        current_price = base_price
        current_time = start_time
        interval_delta = _INTERVAL_DELTAS[interval]

        bars: list[MarketBar] = []

        while current_time <= end_time and len(bars) < 10_000:
            percent_change = Decimal(str(random_generator.uniform(-0.015, 0.015)))

            open_price = current_price
            close_price = (open_price * (Decimal("1") + percent_change)).quantize(Decimal("0.0001"))

            price_range = (
                open_price * Decimal(str(random_generator.uniform(0.001, 0.01)))
            ).quantize(Decimal("0.0001"))

            high_price = (
                max(
                    open_price,
                    close_price,
                )
                + price_range
            )

            low_price = max(
                Decimal("0.0001"),
                min(open_price, close_price) - price_range,
            )

            volume = Decimal(str(random_generator.randint(1_000, 1_000_000)))

            bars.append(
                MarketBar(
                    symbol=normalized_symbol,
                    interval=interval,
                    timestamp=current_time,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    close_price=close_price,
                    volume=volume,
                    provider=self.name,
                )
            )

            current_price = close_price
            current_time += interval_delta

        return bars
