from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from finai.api.schemas.paper_account import (
    PaperAccountCreate,
    PaperAccountResponse,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)
from finai.infrastructure.database.repositories.paper_account_repository import (
    PaperAccountRepository,
)


router = APIRouter(
    prefix="/api/v1/paper/accounts",
    tags=["paper-trading"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.post(
    "",
    response_model=PaperAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_paper_account(
    request: PaperAccountCreate,
    session: DatabaseSession,
) -> PaperAccountResponse:
    repository = PaperAccountRepository(session)

    account = repository.create(
        name=request.name,
        initial_cash=request.initial_cash,
        base_currency=(request.base_currency.upper()),
    )

    return PaperAccountResponse.model_validate(account)


@router.get(
    "",
    response_model=list[PaperAccountResponse],
)
def list_paper_accounts(
    session: DatabaseSession,
) -> list[PaperAccountResponse]:
    repository = PaperAccountRepository(session)

    return [PaperAccountResponse.model_validate(account) for account in repository.list_all()]


@router.get(
    "/{account_id}",
    response_model=PaperAccountResponse,
)
def get_paper_account(
    account_id: UUID,
    session: DatabaseSession,
) -> PaperAccountResponse:
    repository = PaperAccountRepository(session)

    account = repository.get_by_id(account_id)

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(f"Paper account not found: {account_id}"),
        )

    return PaperAccountResponse.model_validate(account)
