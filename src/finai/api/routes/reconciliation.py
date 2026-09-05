from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from finai.api.schemas.reconciliation import (
    AccountReconciliationResponse,
)
from finai.application.services.account_reconciliation_service import (
    AccountReconciliationService,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)


router = APIRouter(
    prefix="/api/v1/reconciliation",
    tags=["reconciliation"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.post(
    "/paper/accounts/{account_id}",
    response_model=(AccountReconciliationResponse),
)
def reconcile_paper_account(
    account_id: UUID,
    session: DatabaseSession,
) -> AccountReconciliationResponse:
    service = AccountReconciliationService(session=session)

    try:
        result = service.reconcile(account_id=account_id)

    except LookupError as error:
        raise HTTPException(
            status_code=(status.HTTP_404_NOT_FOUND),
            detail=str(error),
        ) from error

    return AccountReconciliationResponse(**result)
