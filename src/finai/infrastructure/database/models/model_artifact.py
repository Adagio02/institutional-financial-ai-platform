from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import (
    UUID as PostgreSQLUUID,
)
from sqlalchemy.orm import Mapped, mapped_column

from finai.infrastructure.database.engine import Base


class ModelArtifactModel(Base):
    __tablename__ = "model_artifacts"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    training_run_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "training_runs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
        index=True,
    )

    model_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    stage: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="candidate",
        index=True,
    )

    artifact_uri: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    artifact_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    feature_columns: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
    )

    target_column: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    metadata_json: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
