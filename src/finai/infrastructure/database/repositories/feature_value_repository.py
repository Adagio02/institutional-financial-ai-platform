from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from finai.infrastructure.database.models.feature_value import (
    FeatureValueModel,
)


class FeatureValueRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_many(
        self,
        values: Iterable[dict],
    ) -> int:
        records = list(values)

        if not records:
            return 0

        statement = insert(FeatureValueModel).values(records)

        statement = statement.on_conflict_do_update(
            constraint="uq_feature_value_identity",
            set_={
                "feature_value": (statement.excluded.feature_value),
            },
        )

        self._session.execute(statement)
        self._session.commit()

        return len(records)

    def list_for_range(
        self,
        *,
        feature_set_id: UUID,
        instrument_id: UUID,
        start_time: datetime,
        end_time: datetime,
    ) -> list[FeatureValueModel]:
        statement = (
            select(FeatureValueModel)
            .where(
                FeatureValueModel.feature_set_id == feature_set_id,
                FeatureValueModel.instrument_id == instrument_id,
                FeatureValueModel.timestamp >= start_time,
                FeatureValueModel.timestamp <= end_time,
            )
            .order_by(
                FeatureValueModel.timestamp,
                FeatureValueModel.feature_name,
            )
        )

        return list(self._session.scalars(statement))
