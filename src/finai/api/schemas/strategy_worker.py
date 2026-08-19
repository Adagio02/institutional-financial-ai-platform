from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
)


class StrategyWorkerResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: UUID
    worker_id: str

    hostname: str
    process_id: int

    status: str

    processed_count: int
    successful_count: int
    failed_count: int

    last_error: str | None

    started_at: datetime
    last_heartbeat_at: datetime
    stopped_at: datetime | None

    created_at: datetime
    updated_at: datetime


class StrategyWorkerHealthResponse(BaseModel):
    total_workers: int
    running_workers: int
    stale_workers: int
    failed_workers: int
    healthy: bool