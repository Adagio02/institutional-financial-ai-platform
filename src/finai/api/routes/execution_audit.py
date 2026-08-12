from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy.orm import Session

from finai.api.schemas.execution_audit import (
    ExecutionAuditResponse,
)
from finai.infrastructure.database.engine import (
    get_database_session,
)
from finai.infrastructure.database.repositories.execution_audit_repository import (
    ExecutionAuditRepository,
)


router = APIRouter(
    prefix="/api/v1/execution-audit",
    tags=["execution-audit"],
)

DatabaseSession = Annotated[
    Session,
    Depends(get_database_session),
]


@router.get(
    "",
    response_model=list[ExecutionAuditResponse],
)
def list_execution_audit(
    session: DatabaseSession,
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
    ),
) -> list[ExecutionAuditResponse]:
    repository = ExecutionAuditRepository(session)

    return [
        ExecutionAuditResponse.model_validate(event)
        for event in repository.list_recent(limit=limit)
    ]
