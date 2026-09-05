from uuid import UUID

from sqlalchemy.orm import Session

from finai.domain.modeling.enums import (
    ModelStage,
)
from finai.infrastructure.database.repositories.model_artifact_repository import (
    ModelArtifactRepository,
)


class ModelRegistryService:
    def __init__(
        self,
        *,
        session: Session,
    ) -> None:
        self._repository = ModelArtifactRepository(session)

    def update_stage(
        self,
        *,
        model_id: UUID,
        stage: ModelStage,
    ):
        model = self._repository.get_by_id(model_id)

        if model is None:
            raise LookupError(f"Model not found: {model_id}")

        allowed_transitions = {
            "candidate": {
                ModelStage.STAGING,
                ModelStage.REJECTED,
                ModelStage.ARCHIVED,
            },
            "staging": {
                ModelStage.PRODUCTION,
                ModelStage.REJECTED,
                ModelStage.ARCHIVED,
            },
            "production": {
                ModelStage.ARCHIVED,
            },
            "rejected": {
                ModelStage.ARCHIVED,
            },
            "archived": set(),
        }

        current_stage = model.stage
        allowed = allowed_transitions.get(
            current_stage,
            set(),
        )

        if stage not in allowed:
            raise ValueError(f"Invalid model stage transition: {current_stage} -> {stage.value}")

        return self._repository.update_stage(
            model,
            stage=stage.value,
        )
