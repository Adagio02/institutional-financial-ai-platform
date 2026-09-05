from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from finai.api.schemas.portfolio import (
    PortfolioResponse,
)
from finai.application.services.portfolio_service import (
    PortfolioService,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)


router = APIRouter(
    prefix="/api/v1/paper/portfolio",
    tags=["paper-trading"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.get(
    "/{account_id}",
    response_model=PortfolioResponse,
)
def get_portfolio(
    account_id: UUID,
    session: DatabaseSession,
) -> PortfolioResponse:
    service = PortfolioService(session=session)

    try:
        portfolio = service.summarize(account_id=account_id)

    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    return PortfolioResponse(**portfolio)
