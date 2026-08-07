from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PredictionResult:
    prediction_id: UUID
    model_id: UUID
    dataset_id: UUID
    prediction_timestamp: datetime
    raw_prediction: float
    probability: float | None
    confidence: float | None
    feature_values: dict[str, float]


@dataclass(frozen=True, slots=True)
class ExplanationResult:
    prediction_id: UUID
    explanation_type: str
    baseline_value: float | None
    contributions: dict[str, float]
    metadata: dict[str, Any]
