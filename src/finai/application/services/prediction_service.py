from datetime import datetime
from uuid import UUID

import numpy as np
from sqlalchemy.orm import Session

from finai.domain.prediction.validation import (
    validate_feature_schema,
    validate_prediction_frame,
)
from finai.infrastructure.database.repositories.dataset_version_repository import (
    DatasetVersionRepository,
)
from finai.infrastructure.database.repositories.instrument_repository import (
    InstrumentRepository,
)
from finai.infrastructure.database.repositories.model_artifact_repository import (
    ModelArtifactRepository,
)
from finai.infrastructure.database.repositories.prediction_repository import (
    PredictionRepository,
)
from finai.infrastructure.prediction.feature_loader import (
    FeatureLoader,
)
from finai.infrastructure.prediction.model_loader import (
    ModelLoader,
)


class PredictionService:
    def __init__(
        self,
        *,
        session: Session,
    ) -> None:
        self._model_repository = ModelArtifactRepository(session)
        self._dataset_repository = DatasetVersionRepository(session)
        self._instrument_repository = InstrumentRepository(session)
        self._prediction_repository = PredictionRepository(session)
        self._model_loader = ModelLoader()
        self._feature_loader = FeatureLoader()

    def predict(
        self,
        *,
        model_id: UUID,
        dataset_id: UUID,
        symbol: str,
        prediction_timestamp: datetime | None,
        forecast_horizon: str,
    ):
        model_artifact = self._model_repository.get_by_id(model_id)

        if model_artifact is None:
            raise LookupError(f"Model not found: {model_id}")

        if model_artifact.stage not in {
            "staging",
            "production",
        }:
            raise ValueError("Predictions require a staging or production model.")

        dataset = self._dataset_repository.get_by_id(dataset_id)

        if dataset is None:
            raise LookupError(f"Dataset not found: {dataset_id}")

        if dataset.status != "completed":
            raise ValueError("Predictions require a completed dataset.")

        if not dataset.storage_uri:
            raise ValueError("Dataset does not have a storage URI.")

        expected_dataset_id = model_artifact.metadata_json.get("dataset_id")

        if expected_dataset_id and expected_dataset_id != str(dataset.id):
            raise ValueError("The selected dataset does not match the model's training lineage.")

        instrument = self._instrument_repository.get_model_by_symbol(symbol.strip().upper())

        timestamp, feature_frame = self._feature_loader.load_latest_row(
            dataset_uri=dataset.storage_uri,
            feature_columns=list(model_artifact.feature_columns),
            prediction_timestamp=prediction_timestamp,
        )

        validate_feature_schema(
            frame=feature_frame,
            expected_columns=list(model_artifact.feature_columns),
        )

        validate_prediction_frame(feature_frame)

        model = self._model_loader.load(
            artifact_uri=model_artifact.artifact_uri,
            artifact_hash=model_artifact.artifact_hash,
        )

        prediction_array = model.predict(feature_frame)

        raw_prediction = float(np.asarray(prediction_array)[0])

        probability = None
        confidence = None

        if hasattr(model, "predict_proba"):
            probability_matrix = model.predict_proba(feature_frame)

            probability = float(probability_matrix[0, 1])

            confidence = max(
                probability,
                1.0 - probability,
            )

        feature_values = {
            column: float(feature_frame.iloc[0][column])
            for column in model_artifact.feature_columns
        }

        return self._prediction_repository.create(
            model_id=model_artifact.id,
            dataset_id=dataset.id,
            instrument_id=instrument.id,
            symbol=instrument.symbol,
            prediction_timestamp=timestamp,
            forecast_horizon=forecast_horizon,
            raw_prediction=raw_prediction,
            probability=probability,
            confidence=confidence,
            feature_values=feature_values,
            model_hash=model_artifact.artifact_hash,
        )
