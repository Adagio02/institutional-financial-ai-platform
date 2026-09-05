from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.dataset_version import (
    DatasetVersionModel,
)


class DatasetVersionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        name: str,
        feature_set_id: UUID,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
        configuration: dict,
    ) -> DatasetVersionModel:
        normalized_name = name.strip()

        latest_version = self.get_latest_version(normalized_name)

        dataset = DatasetVersionModel(
            name=normalized_name,
            version=latest_version + 1,
            feature_set_id=feature_set_id,
            symbol=symbol.strip().upper(),
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            row_count=0,
            status="building",
            configuration=configuration,
        )

        self._session.add(dataset)
        self._session.commit()
        self._session.refresh(dataset)

        return dataset

    def get_by_id(
        self,
        dataset_id: UUID,
    ) -> DatasetVersionModel | None:
        return self._session.get(
            DatasetVersionModel,
            dataset_id,
        )

    def get_latest_version(
        self,
        name: str,
    ) -> int:
        statement = (
            select(DatasetVersionModel.version)
            .where(DatasetVersionModel.name == name.strip())
            .order_by(DatasetVersionModel.version.desc())
            .limit(1)
        )

        version = self._session.scalar(statement)

        return int(version or 0)

    def list_all(
        self,
    ) -> list[DatasetVersionModel]:
        statement = select(DatasetVersionModel).order_by(DatasetVersionModel.created_at.desc())

        return list(self._session.scalars(statement))

    def mark_completed(
        self,
        dataset: DatasetVersionModel,
        *,
        row_count: int,
        schema_hash: str,
        content_hash: str,
        storage_uri: str,
    ) -> DatasetVersionModel:
        dataset.status = "completed"
        dataset.row_count = row_count
        dataset.schema_hash = schema_hash
        dataset.content_hash = content_hash
        dataset.storage_uri = storage_uri
        dataset.completed_at = datetime.now(UTC)
        dataset.error_message = None

        self._session.commit()
        self._session.refresh(dataset)

        return dataset

    def mark_failed(
        self,
        dataset: DatasetVersionModel,
        *,
        error_message: str,
    ) -> DatasetVersionModel:
        dataset.status = "failed"
        dataset.error_message = error_message[:4000]
        dataset.completed_at = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(dataset)

        return dataset
