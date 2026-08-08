from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Float,
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


class BacktestRunModel(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    model_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "model_artifacts.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
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

    symbol: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    initial_capital: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    final_equity: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    total_return: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    maximum_drawdown: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    sharpe_ratio: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    trade_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    configuration: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    metrics: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
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
