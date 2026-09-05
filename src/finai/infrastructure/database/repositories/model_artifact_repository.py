from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.model_artifact import (
    ModelArtifactModel,
)


class ModelArtifactRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        training_run_id: UUID,
        model_type: str,
        artifact_uri: str,
        artifact_hash: str,
        feature_columns: list[str],
        target_column: str,
        metadata_json: dict,
    ) -> ModelArtifactModel:
        artifact = ModelArtifactModel(
            training_run_id=training_run_id,
            model_type=model_type,
            stage="candidate",
            artifact_uri=artifact_uri,
            artifact_hash=artifact_hash,
            feature_columns=feature_columns,
            target_column=target_column,
            metadata_json=metadata_json,
        )

        self._session.add(artifact)
        self._session.commit()
        self._session.refresh(artifact)

        return artifact

    def get_by_id(
        self,
        model_id: UUID,
    ) -> ModelArtifactModel | None:
        return self._session.get(
            ModelArtifactModel,
            model_id,
        )

    def list_all(
        self,
    ) -> list[ModelArtifactModel]:
        statement = select(ModelArtifactModel).order_by(ModelArtifactModel.created_at.desc())

        return list(self._session.scalars(statement))

    def update_stage(
        self,
        model: ModelArtifactModel,
        *,
        stage: str,
    ) -> ModelArtifactModel:
        model.stage = stage

        self._session.commit()
        self._session.refresh(model)

        return model
