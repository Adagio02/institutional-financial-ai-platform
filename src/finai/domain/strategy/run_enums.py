from enum import StrEnum


class StrategyRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class StrategyRunItemStatus(StrEnum):
    PENDING = "pending"
    PROPOSAL_CREATED = "proposal_created"
    FAILED = "failed"
