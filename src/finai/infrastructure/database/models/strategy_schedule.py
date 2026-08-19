from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import (
    UUID as PostgreSQLUUID,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from finai.infrastructure.database.engine import (
    Base,
)


class StrategyScheduleModel(Base):
    __tablename__ = "strategy_schedules"

    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "strategy_key",
            "name",
            name="uq_strategy_schedules_account_strategy_name",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    account_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "paper_accounts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    strategy_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    frequency: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )