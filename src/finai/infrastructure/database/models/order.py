from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
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


class OrderModel(Base):
    __tablename__ = "orders"

    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "client_order_id",
            name=("uq_orders_account_client_order_id"),
        ),
    )
    strategy_key: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
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

    instrument_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "instruments.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    client_order_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    broker_order_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    broker_name: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    symbol: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    side: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    order_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    quantity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    filled_quantity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    remaining_quantity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    limit_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    average_fill_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    reference_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    reference_price_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    reference_price_provider: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    time_in_force: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="day",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
    )

    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_synced_at: Mapped[datetime | None] = mapped_column(
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
