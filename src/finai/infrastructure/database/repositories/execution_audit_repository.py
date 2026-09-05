from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.execution_audit import (
    ExecutionAuditModel,
)


class ExecutionAuditRepository:
    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def create(
        self,
        *,
        event_type: str,
        message: str,
        account_id: UUID | None = None,
        order_id: UUID | None = None,
        event_data: dict[
            str,
            Any,
        ]
        | None = None,
    ) -> ExecutionAuditModel:
        event = ExecutionAuditModel(
            account_id=account_id,
            order_id=order_id,
            event_type=event_type,
            message=message,
            event_data=(event_data or {}),
        )

        self._session.add(event)
        self._session.commit()
        self._session.refresh(event)

        return event

    def list_recent(
        self,
        *,
        limit: int = 100,
    ) -> list[ExecutionAuditModel]:
        statement = (
            select(ExecutionAuditModel).order_by(ExecutionAuditModel.created_at.desc()).limit(limit)
        )

        return list(self._session.scalars(statement).all())
