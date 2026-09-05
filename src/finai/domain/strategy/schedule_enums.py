from enum import StrEnum


class StrategyScheduleFrequency(StrEnum):
    HOURLY = "hourly"
    DAILY = "daily"


class StrategyScheduleRunStatus(StrEnum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"