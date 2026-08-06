from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
)

from finai.domain.modeling.enums import (
    ModelStage,
)


class ModelArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    training_run_id: UUID
    model_type: str
    stage: str
    artifact_uri: str
    artifact_hash: str
    feature_columns: list[str]
    target_column: str
    metadata_json: dict[str, Any]
    created_at: datetime


class ModelStageUpdate(BaseModel):
    stage: ModelStage
