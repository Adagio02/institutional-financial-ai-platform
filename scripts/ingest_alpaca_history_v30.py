from __future__ import annotations

import argparse
from datetime import (
    UTC,
    datetime,
    timedelta,
)
from decimal import Decimal
from typing import Any

from finai.core.config import (
    get_settings,
)
from finai.domain.market_data.entities import (
    MarketBar,
)
from finai.domain.market_data.enums import (
    BarInterval,
)
from finai.infrastructure.database.engine import (
    SessionLocal,
)
from finai.infrastructure.database.repositories.instrument_repository import (
    InstrumentRepository,
)
from finai.infrastructure.database.repositories.market_bar_repository import (
    MarketBarRepository,
)
from finai.infrastructure.market_data.alpaca_market_data_client import (
    AlpacaMarketDataClient,
)


PROVIDER = "alpaca"
DATABASE_BATCH_SIZE = 500


def parse_timestamp(
    value: str,
) -> datetime:
    normalized = (
        value
        .strip()
        .replace(
            "Z",
            "+00:00",
        )
    )

    timestamp = datetime.fromisoformat(
        normalized
    )

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(
            tzinfo=UTC
        )

    return timestamp.astimezone(
        UTC
    )


def to_decimal(
    value: Any,
) -> Decimal:
    return Decimal(
        str(value)
    )


def create_market_bar(
    *,
    symbol: str,
    raw: dict[str, Any],
    interval: BarInterval,
) -> MarketBar:
    normalized_symbol = (
        symbol
        .strip()
        .upper()
    )

    if not normalized_symbol:
        raise ValueError(
            "symbol cannot be blank."
        )

    required_fields = {
        "t",
        "o",
        "h",
        "l",
        "c",
        "v",
    }

    missing_fields = (
        required_fields
        - set(raw)
    )

    if missing_fields:
        raise ValueError(
            "Alpaca bar is missing fields: "
            f"{sorted(missing_fields)}"
        )

    return MarketBar(
        symbol=normalized_symbol,
        interval=interval,
        timestamp=parse_timestamp(
            str(
                raw["t"]
            )
        ),
        open_price=to_decimal(
            raw["o"]
        ),
        high_price=to_decimal(
            raw["h"]
        ),
        low_price=to_decimal(
            raw["l"]
        ),
        close_price=to_decimal(
            raw["c"]
        ),
        volume=to_decimal(
            raw["v"]
        ),
        provider=PROVIDER,
    )


def alpaca_timeframe(
    interval: BarInterval,
) -> str:
    mapping = {
        BarInterval.ONE_MINUTE: (
            "1Min"
        ),
        BarInterval.FIVE_MINUTES: (
            "5Min"
        ),
        BarInterval.FIFTEEN_MINUTES: (
            "15Min"
        ),
        BarInterval.ONE_HOUR: (
            "1Hour"
        ),
        BarInterval.ONE_DAY: (
            "1Day"
        ),
    }

    return mapping[
        interval
    ]


def isoformat_utc(
    value: datetime,
) -> str:
    return (
        value
        .astimezone(UTC)
        .isoformat()
        .replace(
            "+00:00",
            "Z",
        )
    )


def ingest(
    *,
    symbol: str,
    interval: BarInterval,
    days: int,
) -> None:
    if days <= 0:
        raise ValueError(
            "days must be greater than zero."
        )

    normalized_symbol = (
        symbol
        .strip()
        .upper()
    )

    if not normalized_symbol:
        raise ValueError(
            "symbol cannot be blank."
        )

    settings = get_settings()

    client = (
        AlpacaMarketDataClient(
            api_key=(
                settings.alpaca_api_key
            ),
            secret_key=(
                settings.alpaca_secret_key
            ),
            base_url=(
                settings.alpaca_data_base_url
            ),
            feed=(
                settings.alpaca_market_data_feed
            ),
            timeout_seconds=(
                settings
                .alpaca_request_timeout_seconds
            ),
        )
    )

    end_time = datetime.now(
        UTC
    )

    start_time = (
        end_time
        - timedelta(
            days=days
        )
    )

    start_value = isoformat_utc(
        start_time
    )

    end_value = isoformat_utc(
        end_time
    )

    session = SessionLocal()

    try:
        instrument_repository = (
            InstrumentRepository(
                session
            )
        )

        market_bar_repository = (
            MarketBarRepository(
                session
            )
        )

        instrument = (
            instrument_repository
            .get_model_by_symbol(
                normalized_symbol
            )
        )

        if instrument is None:
            raise LookupError(
                "Instrument not found: "
                f"{normalized_symbol}"
            )

        page_token: str | None = None

        total_received = 0
        total_upserted = 0
        page_number = 0

        while True:
            page_number += 1

            response = (
                client
                .get_historical_bars(
                    symbol=(
                        normalized_symbol
                    ),
                    timeframe=(
                        alpaca_timeframe(
                            interval
                        )
                    ),
                    start=(
                        start_value
                    ),
                    end=(
                        end_value
                    ),
                    limit=10_000,
                    page_token=(
                        page_token
                    ),
                )
            )

            raw_bars = response.get(
                "bars",
                [],
            )

            if not raw_bars:
                break

            bars = [
                create_market_bar(
                    symbol=(
                        normalized_symbol
                    ),
                    raw=raw,
                    interval=(
                        interval
                    ),
                )
                for raw
                in raw_bars
            ]

            received = len(
                bars
            )

            upserted = 0

            for batch_start in range(
                0,
                len(bars),
                DATABASE_BATCH_SIZE,
            ):
                batch_end = (
                    batch_start
                    + DATABASE_BATCH_SIZE
                )

                batch = bars[
                    batch_start:batch_end
                ]

                batch_upserted = (
                    market_bar_repository
                    .upsert_many(
                        instrument=(
                            instrument
                        ),
                        bars=batch,
                    )
                )

                upserted += (
                    batch_upserted
                )

                print(
                    "Database batch stored: "
                    f"rows={len(batch)}, "
                    f"page={page_number}"
                )

            total_received += (
                received
            )

            total_upserted += (
                upserted
            )

            print(
                "Stored Alpaca bars: "
                f"page={page_number}, "
                f"batch={received}, "
                f"total_received="
                f"{total_received}, "
                f"total_upserted="
                f"{total_upserted}"
            )

            next_page_token = (
                response.get(
                    "next_page_token"
                )
            )

            if not next_page_token:
                break

            page_token = str(
                next_page_token
            )

        print()

        print(
            "V3.0 Alpaca historical "
            "ingestion complete."
        )

        print(
            f"symbol="
            f"{normalized_symbol}"
        )

        print(
            f"interval="
            f"{interval.value}"
        )

        print(
            f"provider="
            f"{PROVIDER}"
        )

        print(
            f"received="
            f"{total_received}"
        )

        print(
            f"upserted="
            f"{total_upserted}"
        )

        print(
            f"start="
            f"{start_value}"
        )

        print(
            f"end="
            f"{end_value}"
        )

        if total_received == 0:
            raise RuntimeError(
                "Alpaca returned zero "
                "historical bars."
            )

    finally:
        session.close()


def main() -> None:
    parser = (
        argparse
        .ArgumentParser()
    )

    parser.add_argument(
        "--symbol",
        default="AAPL",
    )

    parser.add_argument(
        "--interval",
        default="1m",
        choices=[
            interval.value
            for interval
            in BarInterval
        ],
    )

    parser.add_argument(
        "--days",
        type=int,
        default=10,
    )

    arguments = (
        parser
        .parse_args()
    )

    ingest(
        symbol=(
            arguments.symbol
        ),
        interval=BarInterval(
            arguments.interval
        ),
        days=(
            arguments.days
        ),
    )


if __name__ == "__main__":
    main()