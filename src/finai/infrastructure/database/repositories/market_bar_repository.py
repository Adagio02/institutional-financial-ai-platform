from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from finai.domain.market_data.entities import MarketBar
from finai.domain.market_data.enums import BarInterval
from finai.domain.market_data.validation import validate_market_bar
from finai.infrastructure.database.models.instrument import InstrumentModel
from finai.infrastructure.database.models.market_bar import MarketBarModel


class MarketBarRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def upsert_many(
        self,
        *,
        instrument: InstrumentModel,
        bars: list[MarketBar],
    ) -> int:
        if not bars:
            return 0

        for bar in bars:
            validate_market_bar(bar)

        values = [
            {
                "instrument_id": instrument.id,
                "interval": bar.interval.value,
                "timestamp": bar.timestamp,
                "open_price": bar.open_price,
                "high_price": bar.high_price,
                "low_price": bar.low_price,
                "close_price": bar.close_price,
                "volume": bar.volume,
                "provider": bar.provider,
            }
            for bar in bars
        ]

        statement = insert(
            MarketBarModel
        ).values(values)

        statement = (
            statement.on_conflict_do_update(
                constraint="uq_market_bars_identity",
                set_={
                    "open_price": (
                        statement.excluded.open_price
                    ),
                    "high_price": (
                        statement.excluded.high_price
                    ),
                    "low_price": (
                        statement.excluded.low_price
                    ),
                    "close_price": (
                        statement.excluded.close_price
                    ),
                    "volume": (
                        statement.excluded.volume
                    ),
                    "provider": (
                        statement.excluded.provider
                    ),
                },
            )
        )

        self._session.execute(
            statement
        )

        self._session.commit()

        return len(values)

    def get_bars(
        self,
        *,
        instrument_id: object,
        interval: BarInterval,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
    ) -> list[MarketBarModel]:
        statement = (
            select(MarketBarModel)
            .where(
                MarketBarModel.instrument_id
                == instrument_id,
                MarketBarModel.interval
                == interval.value,
            )
            .order_by(
                MarketBarModel.timestamp
            )
            .limit(limit)
        )

        if start_time is not None:
            statement = statement.where(
                MarketBarModel.timestamp
                >= start_time
            )

        if end_time is not None:
            statement = statement.where(
                MarketBarModel.timestamp
                <= end_time
            )

        return list(
            self._session.scalars(
                statement
            ).all()
        )

    def get_latest_bar(
        self,
        *,
        instrument_id: object,
        interval: BarInterval,
    ) -> MarketBarModel | None:
        statement = (
            select(MarketBarModel)
            .where(
                MarketBarModel.instrument_id
                == instrument_id,
                MarketBarModel.interval
                == interval.value,
            )
            .order_by(
                MarketBarModel.timestamp.desc()
            )
            .limit(1)
        )

        return self._session.scalar(
            statement
        )