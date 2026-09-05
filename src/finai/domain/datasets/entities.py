from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DatasetBuildResult:
    dataset_id: UUID
    name: str
    version: int
    row_count: int
    schema_hash: str
    content_hash: str
    storage_uri: str
    start_time: datetime
    end_time: datetime
