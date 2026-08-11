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
    FillResponse,
    OrderCreate,
    OrderResponse,
)
from finai.application.services.order_service import (
    OrderService,
)
from finai.core.config import get_settings
from finai.domain.portfolio.risk_limits import (
    PortfolioRiskLimits,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)
from finai.infrastructure.database.repositories.execution_fill_repository import (
    ExecutionFillRepository,
)
from finai.infrastructure.database.repositories.order_repository import (
    OrderRepository,
)


router = APIRouter(
    prefix="/api/v1/paper/orders",
    tags=["paper-trading"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_order(
    request: OrderCreate,
    session: DatabaseSession,
) -> OrderResponse:
    settings = get_settings()

    risk_limits = PortfolioRiskLimits(
        maximum_order_notional=(settings.paper_maximum_order_notional),
        maximum_position_notional=(settings.paper_maximum_position_notional),
        maximum_gross_exposure=(settings.paper_maximum_gross_exposure),
        maximum_position_fraction=(settings.paper_maximum_position_fraction),
        minimum_cash_reserve_fraction=(settings.paper_minimum_cash_reserve_fraction),
    )

    service = OrderService(
        session=session,
        commission_bps=(settings.paper_trading_commission_bps),
        slippage_bps=(settings.paper_trading_slippage_bps),
        risk_limits=risk_limits,
    )

    try:
        order = service.submit(
            account_id=request.account_id,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=request.quantity,
            reference_price=(request.reference_price),
            limit_price=request.limit_price,
            time_in_force=(request.time_in_force),
        )

    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return OrderResponse.model_validate(order)


@router.get(
    "/account/{account_id}",
    response_model=list[OrderResponse],
)
def list_orders(
    account_id: UUID,
    session: DatabaseSession,
) -> list[OrderResponse]:
    repository = OrderRepository(session)

    return [
        OrderResponse.model_validate(order) for order in repository.list_for_account(account_id)
    ]


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
def get_order(
    order_id: UUID,
    session: DatabaseSession,
) -> OrderResponse:
    repository = OrderRepository(session)

    order = repository.get_by_id(order_id)

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"Order not found: {order_id}"),
        )

    return OrderResponse.model_validate(order)


@router.get(
    "/{order_id}/fills",
    response_model=list[FillResponse],
)
def list_order_fills(
    order_id: UUID,
    session: DatabaseSession,
) -> list[FillResponse]:
    repository = ExecutionFillRepository(session)

    return [FillResponse.model_validate(fill) for fill in repository.list_for_order(order_id)]
