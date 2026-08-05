from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from finai.infrastructure.database.engine import Base


class FeatureValueModel(Base):
    __tablename__ = "feature_values"

    __table_args__ = (
        UniqueConstraint(
            "feature_set_id",
            "instrument_id",
            "timestamp",
            "feature_name",
            name="uq_feature_value_identity",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    feature_set_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "feature_sets.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    instrument_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "instruments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    feature_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    feature_value: Mapped[Decimal | None] = mapped_column(
        Numeric(28, 12),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
