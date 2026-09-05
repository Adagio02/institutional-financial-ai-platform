from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import (
    UUID as PostgreSQLUUID,
)
from sqlalchemy.orm import Mapped, mapped_column

from finai.infrastructure.database.engine import Base


class TrainingRunModel(Base):
    __tablename__ = "training_runs"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    dataset_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "dataset_versions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    model_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    prediction_task: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    target_column: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    feature_columns: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )

    parameters: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    number_of_splits: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    test_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    random_seed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
    )

    mlflow_run_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
