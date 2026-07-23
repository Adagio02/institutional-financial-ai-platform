from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from finai.api.schemas.market_data import (
    MarketBarCollectionResponse,
    MarketBarResponse,
    MarketDataIngestionRequest,
    MarketDataIngestionResponse,
)
from finai.application.market_data.ingestion_service import (
    MarketDataIngestionService,
)
from finai.core.config import get_settings
from finai.domain.market_data.enums import BarInterval
from finai.infrastructure.database.engine import get_database_session
from finai.infrastructure.database.repositories.exceptions import (
    InstrumentNotFoundError,
)
from finai.infrastructure.database.repositories.instrument_repository import (
    InstrumentRepository,
)
from finai.infrastructure.database.repositories.market_bar_repository import (
    MarketBarRepository,
)
from finai.infrastructure.market_data.factory import (
    create_market_data_provider,
)


router = APIRouter(
    prefix="/api/v1/market-data",
    tags=["market-data"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.post(
    "/ingest",
    response_model=MarketDataIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_market_data(
    request: MarketDataIngestionRequest,
    session: DatabaseSession,
) -> MarketDataIngestionResponse:
    settings = get_settings()

    provider = create_market_data_provider(settings.market_data_provider)

    service = MarketDataIngestionService(
        session=session,
        provider=provider,
        maximum_bars=settings.market_data_max_bars_per_request,
    )

    try:
        result = service.ingest(
            symbol=request.symbol,
            interval=request.interval,
            start_time=request.start_time,
            end_time=request.end_time,
        )
    except InstrumentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    return MarketDataIngestionResponse(
        symbol=result.symbol,
        interval=result.interval,
        provider=result.provider,
        bars_received=result.bars_received,
        bars_persisted=result.bars_persisted,
        start_time=result.start_time,
        end_time=result.end_time,
    )


@router.get(
    "/bars",
    response_model=MarketBarCollectionResponse,
)
def get_market_bars(
    session: DatabaseSession,
    symbol: Annotated[str, Query(min_length=1, max_length=32)],
    interval: Annotated[BarInterval, Query()],
    start_time: Annotated[datetime | None, Query()] = None,
    end_time: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=10_000)] = 500,
) -> MarketBarCollectionResponse:
    instrument_repository = InstrumentRepository(session)
    bar_repository = MarketBarRepository(session)

    try:
        instrument = instrument_repository.get_model_by_symbol(symbol)
    except InstrumentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    bars = bar_repository.get_bars(
        instrument_id=instrument.id,
        interval=interval,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )

    response_bars = [
        MarketBarResponse(
            symbol=instrument.symbol,
            interval=BarInterval(bar.interval),
            timestamp=bar.timestamp,
            open_price=bar.open_price,
            high_price=bar.high_price,
            low_price=bar.low_price,
            close_price=bar.close_price,
            volume=bar.volume,
            provider=bar.provider,
        )
        for bar in bars
    ]

    return MarketBarCollectionResponse(
        symbol=instrument.symbol,
        interval=interval,
        count=len(response_bars),
        bars=response_bars,
    )
