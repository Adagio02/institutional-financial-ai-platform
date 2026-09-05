import pandas as pd
from sqlalchemy.orm import Session

from finai.infrastructure.database.repositories.model_artifact_repository import (
    ModelArtifactRepository,
)
from finai.infrastructure.database.repositories.prediction_explanation_repository import (
    PredictionExplanationRepository,
)
from finai.infrastructure.database.repositories.prediction_repository import (
    PredictionRepository,
)
from finai.infrastructure.prediction.explainer import (
    calculate_feature_contributions,
)
from finai.infrastructure.prediction.model_loader import (
    ModelLoader,
)


class ExplanationService:
    def __init__(
        self,
        *,
        session: Session,
    ) -> None:
        self._prediction_repository = PredictionRepository(session)
        self._model_repository = ModelArtifactRepository(session)
        self._explanation_repository = PredictionExplanationRepository(session)
        self._model_loader = ModelLoader()

    def explain(
        self,
        *,
        prediction_id,
    ):
        prediction = self._prediction_repository.get_by_id(prediction_id)

        if prediction is None:
            raise LookupError(f"Prediction not found: {prediction_id}")

        model_artifact = self._model_repository.get_by_id(prediction.model_id)

        if model_artifact is None:
            raise LookupError(f"Model not found: {prediction.model_id}")

        model = self._model_loader.load(
            artifact_uri=model_artifact.artifact_uri,
            artifact_hash=model_artifact.artifact_hash,
        )

        feature_frame = pd.DataFrame(
            [
                {
                    column: prediction.feature_values[column]
                    for column in model_artifact.feature_columns
                }
            ],
            columns=model_artifact.feature_columns,
        )

        (
            baseline_value,
            contributions,
            metadata,
        ) = calculate_feature_contributions(
            model=model,
            feature_frame=feature_frame,
        )

        return self._explanation_repository.create(
            prediction_id=prediction.id,
            explanation_type=("feature_contribution"),
            baseline_value=baseline_value,
            contributions=contributions,
            metadata_json=metadata,
        )
