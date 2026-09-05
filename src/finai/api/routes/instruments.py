from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from finai.api.schemas.instrument import (
    InstrumentCreateRequest,
    InstrumentResponse,
)
from finai.domain.market_data.entities import Instrument
from finai.infrastructure.database.engine import get_database_session
from finai.infrastructure.database.repositories.exceptions import (
    InstrumentAlreadyExistsError,
    InstrumentNotFoundError,
)
from finai.infrastructure.database.repositories.instrument_repository import (
    InstrumentRepository,
)


router = APIRouter(
    prefix="/api/v1/instruments",
    tags=["instruments"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.post(
    "",
    response_model=InstrumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_instrument(
    request: InstrumentCreateRequest,
    session: DatabaseSession,
) -> Instrument:
    repository = InstrumentRepository(session)

    instrument = Instrument(
        symbol=request.symbol,
        name=request.name,
        asset_class=request.asset_class,
        exchange=request.exchange,
        currency=request.currency,
    )

    try:
        return repository.create(instrument)
    except InstrumentAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error


@router.get(
    "",
    response_model=list[InstrumentResponse],
)
def list_instruments(
    session: DatabaseSession,
    active_only: Annotated[bool, Query()] = True,
) -> list[Instrument]:
    repository = InstrumentRepository(session)

    return repository.list_all(active_only=active_only)


@router.get(
    "/{symbol}",
    response_model=InstrumentResponse,
)
def get_instrument(
    symbol: str,
    session: DatabaseSession,
) -> Instrument:
    repository = InstrumentRepository(session)

    try:
        return repository.get_by_symbol(symbol)
    except InstrumentNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
