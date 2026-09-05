from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.feature_set import (
    FeatureSetModel,
)


class FeatureSetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        name: str,
        description: str | None,
        configuration: dict,
    ) -> FeatureSetModel:
        normalized_name = name.strip()

        latest_version = self.get_latest_version(normalized_name)

        feature_set = FeatureSetModel(
            name=normalized_name,
            description=description,
            version=latest_version + 1,
            configuration=configuration,
        )

        self._session.add(feature_set)
        self._session.commit()
        self._session.refresh(feature_set)

        return feature_set

    def get_by_id(
        self,
        feature_set_id: UUID,
    ) -> FeatureSetModel | None:
        return self._session.get(
            FeatureSetModel,
            feature_set_id,
        )

    def get_latest_version(
        self,
        name: str,
    ) -> int:
        statement = (
            select(FeatureSetModel.version)
            .where(FeatureSetModel.name == name.strip())
            .order_by(FeatureSetModel.version.desc())
            .limit(1)
        )

        version = self._session.scalar(statement)

        return int(version or 0)

    def list_all(self) -> list[FeatureSetModel]:
        statement = select(FeatureSetModel).order_by(FeatureSetModel.created_at.desc())

        return list(self._session.scalars(statement))
