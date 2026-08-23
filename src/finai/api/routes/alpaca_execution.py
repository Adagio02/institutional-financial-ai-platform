from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from finai.api.schemas.order import (
    OrderResponse,
)
from finai.application.services.alpaca_order_execution_service import (
    AlpacaOrderExecutionService,
)
from finai.core.config import (
    get_settings,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)
from finai.infrastructure.database.repositories.order_repository import (
    OrderRepository,
)
from finai.infrastructure.execution.alpaca_broker import (
    AlpacaPaperBroker,
)
from finai.infrastructure.execution.alpaca_client import (
    AlpacaApiError,
    AlpacaPaperClient,
)


router = APIRouter(
    prefix="/api/v1/alpaca-paper",
    tags=["alpaca-paper"],
)


DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


def build_alpaca_broker(
) -> AlpacaPaperBroker:
    settings = get_settings()

    if not (
        settings
        .alpaca_paper_trading_enabled
    ):
        raise ValueError(
            "Alpaca paper integration "
            "is disabled."
        )

    client = AlpacaPaperClient(
        api_key=settings.alpaca_api_key,
        secret_key=(
            settings.alpaca_secret_key
        ),
        base_url=(
            settings.alpaca_base_url
        ),
        timeout_seconds=(
            settings
            .alpaca_request_timeout_seconds
        ),
    )

    return AlpacaPaperBroker(
        client=client
    )


def build_execution_service(
    *,
    session: Session,
) -> AlpacaOrderExecutionService:
    settings = get_settings()

    return AlpacaOrderExecutionService(
        session=session,
        broker=build_alpaca_broker(),
        commission_bps=(
            settings
            .alpaca_execution_commission_bps
        ),
        sync_on_submit=(
            settings.alpaca_sync_on_submit
        ),
    )


@router.get(
    "/account",
)
def alpaca_account():
    try:
        return (
            build_alpaca_broker()
            .account()
        )

    except (
        ValueError,
        AlpacaApiError,
    ) as error:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail=str(error),
        ) from error


@router.post(
    "/orders/{order_id}/sync",
    response_model=OrderResponse,
)
def sync_alpaca_order(
    order_id: UUID,
    session: DatabaseSession,
) -> OrderResponse:
    repository = OrderRepository(
        session
    )

    order = repository.get_by_id(
        order_id
    )

    if order is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                f"Order not found: "
                f"{order_id}"
            ),
        )

    try:
        updated = (
            build_execution_service(
                session=session
            )
            .sync(
                order=order
            )
        )

    except AlpacaApiError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=str(error),
        ) from error

    return OrderResponse.model_validate(
        updated
    )