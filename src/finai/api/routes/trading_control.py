from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from finai.api.schemas.trading_control import (
    KillSwitchRequest,
    TradingControlResponse,
    TradingEnabledUpdate,
)
from finai.application.services.trading_control_service import (
    TradingControlService,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)


router = APIRouter(
    prefix="/api/v1/trading-control",
    tags=["trading-control"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


def _to_response(
    state,
) -> TradingControlResponse:
    return TradingControlResponse(
        trading_enabled=(state.trading_enabled),
        kill_switch_active=(state.kill_switch_active),
        reason=state.reason,
        can_trade=state.can_trade,
    )


@router.get(
    "",
    response_model=(TradingControlResponse),
)
def get_trading_control(
    session: DatabaseSession,
) -> TradingControlResponse:
    service = TradingControlService(session=session)

    return _to_response(service.get_state())


@router.put(
    "/enabled",
    response_model=(TradingControlResponse),
)
def set_trading_enabled(
    request: TradingEnabledUpdate,
    session: DatabaseSession,
) -> TradingControlResponse:
    service = TradingControlService(session=session)

    try:
        state = service.set_trading_enabled(
            enabled=request.enabled,
            reason=request.reason,
        )

    except ValueError as error:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=str(error),
        ) from error

    return _to_response(state)


@router.post(
    "/kill-switch/activate",
    response_model=(TradingControlResponse),
)
def activate_kill_switch(
    request: KillSwitchRequest,
    session: DatabaseSession,
) -> TradingControlResponse:
    service = TradingControlService(session=session)

    try:
        state = service.activate_kill_switch(reason=request.reason)

    except ValueError as error:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=str(error),
        ) from error

    return _to_response(state)


@router.post(
    "/kill-switch/deactivate",
    response_model=(TradingControlResponse),
)
def deactivate_kill_switch(
    request: KillSwitchRequest,
    session: DatabaseSession,
) -> TradingControlResponse:
    service = TradingControlService(session=session)

    try:
        state = service.deactivate_kill_switch(reason=request.reason)

    except ValueError as error:
        raise HTTPException(
            status_code=(status.HTTP_409_CONFLICT),
            detail=str(error),
        ) from error

    return _to_response(state)
