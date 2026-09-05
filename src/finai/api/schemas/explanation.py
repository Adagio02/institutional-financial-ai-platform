from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PredictionExplanationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    prediction_id: UUID
    explanation_type: str
    baseline_value: float | None
    contributions: dict[str, float]
    metadata_json: dict[str, Any]
    created_at: datetime
