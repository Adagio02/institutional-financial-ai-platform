from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
)


class OrderLifecycleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    broker_order_id: str | None
    broker_name: str | None

    status: str

    quantity: float
    filled_quantity: float
    remaining_quantity: float

    submitted_at: datetime | None
    cancelled_at: datetime | None
    last_synced_at: datetime | None
