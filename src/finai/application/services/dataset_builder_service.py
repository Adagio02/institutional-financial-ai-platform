import hashlib
import json
from datetime import datetime
from pathlib import Path
from uuid import UUID

import pandas as pd
from sqlalchemy.orm import Session

from finai.application.services.dataset_validation_service import (
    DatasetValidationService,
)
from finai.domain.datasets.entities import (
    DatasetBuildResult,
)
from finai.infrastructure.database.repositories.dataset_version_repository import (
    DatasetVersionRepository,
)
from finai.infrastructure.database.repositories.feature_set_repository import (
    FeatureSetRepository,
)
from finai.infrastructure.database.repositories.feature_value_repository import (
    FeatureValueRepository,
)
from finai.infrastructure.database.repositories.instrument_repository import (
    InstrumentRepository,
)


class DatasetBuilderService:
    def __init__(
        self,
        *,
        session: Session,
        output_directory: Path,
    ) -> None:
        self._feature_set_repository = FeatureSetRepository(session)

        self._feature_value_repository = FeatureValueRepository(session)

        self._instrument_repository = InstrumentRepository(session)

        self._dataset_repository = DatasetVersionRepository(session)

        self._validation_service = DatasetValidationService()

        self._output_directory = output_directory

    def build(
        self,
        *,
        name: str,
        feature_set_id: UUID,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
        drop_missing_rows: bool = True,
    ) -> DatasetBuildResult:
        feature_set = self._feature_set_repository.get_by_id(feature_set_id)

        if feature_set is None:
            raise LookupError(f"Feature set not found: {feature_set_id}")

        instrument = self._instrument_repository.get_model_by_symbol(symbol.strip().upper())

        dataset = self._dataset_repository.create(
            name=name,
            feature_set_id=feature_set_id,
            symbol=instrument.symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            configuration={
                "drop_missing_rows": (drop_missing_rows),
            },
        )

        try:
            values = self._feature_value_repository.list_for_range(
                feature_set_id=feature_set_id,
                instrument_id=instrument.id,
                start_time=start_time,
                end_time=end_time,
            )

            frame = self._values_to_frame(values)

            if drop_missing_rows:
                frame = frame.dropna()

            self._validation_service.validate(frame)

            schema_hash = self._calculate_schema_hash(frame)

            content_hash = self._calculate_content_hash(frame)

            storage_path = self._write_dataset(
                dataset_id=dataset.id,
                frame=frame,
            )

            self._dataset_repository.mark_completed(
                dataset,
                row_count=len(frame),
                schema_hash=schema_hash,
                content_hash=content_hash,
                storage_uri=str(storage_path),
            )

            return DatasetBuildResult(
                dataset_id=dataset.id,
                name=dataset.name,
                version=dataset.version,
                row_count=len(frame),
                schema_hash=schema_hash,
                content_hash=content_hash,
                storage_uri=str(storage_path),
                start_time=start_time,
                end_time=end_time,
            )

        except Exception as error:
            self._dataset_repository.mark_failed(
                dataset,
                error_message=str(error),
            )

            raise

    @staticmethod
    def _values_to_frame(
        values,
    ) -> pd.DataFrame:
        rows = [
            {
                "timestamp": value.timestamp,
                "feature_name": (value.feature_name),
                "feature_value": (
                    float(value.feature_value) if value.feature_value is not None else None
                ),
            }
            for value in values
        ]

        if not rows:
            return pd.DataFrame()

        long_frame = pd.DataFrame(rows)

        frame = long_frame.pivot(
            index="timestamp",
            columns="feature_name",
            values="feature_value",
        )

        frame = frame.sort_index()
        frame.columns.name = None

        return frame

    @staticmethod
    def _calculate_schema_hash(
        frame: pd.DataFrame,
    ) -> str:
        schema = {column: str(dtype) for column, dtype in frame.dtypes.items()}

        payload = json.dumps(
            schema,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _calculate_content_hash(
        frame: pd.DataFrame,
    ) -> str:
        normalized = frame.copy()
        normalized = normalized.sort_index()

        normalized = normalized.reindex(
            sorted(normalized.columns),
            axis=1,
        )

        payload = normalized.to_csv(
            index=True,
            date_format="%Y-%m-%dT%H:%M:%S%z",
            float_format="%.12g",
        ).encode("utf-8")

        return hashlib.sha256(payload).hexdigest()

    def _write_dataset(
        self,
        *,
        dataset_id: UUID,
        frame: pd.DataFrame,
    ) -> Path:
        self._output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        path = self._output_directory / f"{dataset_id}.parquet"

        frame.to_parquet(
            path,
            index=True,
        )

        return path
