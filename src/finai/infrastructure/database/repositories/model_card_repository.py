from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.model_card import (
    ModelCardModel,
)


class ModelCardRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        model_id: UUID,
        summary: str,
        intended_use: str,
        limitations: str,
        evaluation_summary: dict,
        governance_metadata: dict,
    ) -> ModelCardModel:
        model_card = ModelCardModel(
            model_id=model_id,
            summary=summary,
            intended_use=intended_use,
            limitations=limitations,
            evaluation_summary=evaluation_summary,
            governance_metadata=governance_metadata,
        )

        self._session.add(model_card)
        self._session.commit()
        self._session.refresh(model_card)

        return model_card

    def get_for_model(
        self,
        model_id: UUID,
    ) -> ModelCardModel | None:
        statement = select(ModelCardModel).where(ModelCardModel.model_id == model_id)

        return self._session.scalar(statement)
