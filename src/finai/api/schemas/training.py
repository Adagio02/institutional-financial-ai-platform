from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from finai.domain.modeling.enums import (
    ModelType,
    PredictionTask,
)


class TrainingRunCreate(BaseModel):
    dataset_id: UUID
    model_type: ModelType
    prediction_task: PredictionTask

    feature_columns: list[str] = Field(min_length=1)

    parameters: dict[str, Any] = Field(default_factory=dict)

    number_of_splits: int = Field(
        default=3,
        ge=1,
        le=20,
    )

    test_size: int = Field(
        default=10,
        ge=1,
    )

    random_seed: int = 42

    @model_validator(mode="after")
    def validate_model_task(
        self,
    ) -> "TrainingRunCreate":
        classification_models = {
            ModelType.LOGISTIC_REGRESSION,
            ModelType.RANDOM_FOREST_CLASSIFIER,
        }

        regression_models = {
            ModelType.LINEAR_REGRESSION,
            ModelType.RANDOM_FOREST_REGRESSOR,
        }

        if (
            self.prediction_task == PredictionTask.CLASSIFICATION
            and self.model_type not in classification_models
        ):
            raise ValueError("Classification requires a classification model.")

        if (
            self.prediction_task == PredictionTask.REGRESSION
            and self.model_type not in regression_models
        ):
            raise ValueError("Regression requires a regression model.")

        return self


class TrainingRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_id: UUID
    model_type: str
    prediction_task: str
    target_column: str
    feature_columns: list[str]
    parameters: dict[str, Any]
    number_of_splits: int
    test_size: int
    random_seed: int
    status: str
    mlflow_run_id: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class TrainingExecutionResponse(BaseModel):
    training_run: TrainingRunResponse
    model_artifact_id: UUID
    metrics: dict[str, float]
