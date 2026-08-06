from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TrainingConfiguration:
    dataset_id: UUID
    model_type: str
    prediction_task: str
    target_column: str
    feature_columns: tuple[str, ...]
    parameters: dict[str, Any]
    number_of_splits: int
    test_size: int
    random_seed: int


@dataclass(frozen=True, slots=True)
class FoldResult:
    fold_number: int
    training_rows: int
    validation_rows: int
    metrics: dict[str, float]


@dataclass(frozen=True, slots=True)
class TrainingResult:
    training_run_id: UUID
    model_artifact_id: UUID
    model_path: str
    metrics: dict[str, float]
    mlflow_run_id: str | None
