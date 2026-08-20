from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
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


class TradingControlModel(Base):
    __tablename__ = "trading_controls"

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
        unique=True,
        index=True,
    )

    trading_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    manual_halt: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    manual_halt_reason: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    circuit_breaker_tripped: Mapped[
        bool
    ] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    circuit_breaker_reason: Mapped[
        str | None
    ] = mapped_column(
        String(64),
        nullable=True,
    )

    circuit_breaker_message: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    circuit_breaker_tripped_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    day_start_date: Mapped[
        date | None
    ] = mapped_column(
        Date,
        nullable=True,
    )

    day_start_equity: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    maximum_daily_loss_fraction: Mapped[
        float
    ] = mapped_column(
        Float,
        nullable=False,
    )

    maximum_gross_exposure_fraction: Mapped[
        float
    ] = mapped_column(
        Float,
        nullable=False,
    )

    maximum_symbol_fraction: Mapped[
        float
    ] = mapped_column(
        Float,
        nullable=False,
    )

    maximum_order_fraction: Mapped[
        float
    ] = mapped_column(
        Float,
        nullable=False,
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