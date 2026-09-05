from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
)


class ExecutionAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    account_id: UUID | None
    order_id: UUID | None

    event_type: str
    message: str

    event_data: dict[
        str,
        Any,
    ]

    created_at: datetime
