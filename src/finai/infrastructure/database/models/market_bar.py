from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from finai.infrastructure.database.engine import Base


class MarketBarModel(Base):
    __tablename__ = "market_bars"

    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "interval",
            "timestamp",
            "provider",
            name="uq_market_bars_identity",
        ),
        Index(
            "ix_market_bars_instrument_interval_timestamp",
            "instrument_id",
            "interval",
            "timestamp",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    instrument_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    interval: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    open_price: Mapped[Decimal] = mapped_column(
        Numeric(24, 10),
        nullable=False,
    )

    high_price: Mapped[Decimal] = mapped_column(
        Numeric(24, 10),
        nullable=False,
    )

    low_price: Mapped[Decimal] = mapped_column(
        Numeric(24, 10),
        nullable=False,
    )

    close_price: Mapped[Decimal] = mapped_column(
        Numeric(24, 10),
        nullable=False,
    )

    volume: Mapped[Decimal] = mapped_column(
        Numeric(30, 10),
        nullable=False,
    )

    provider: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
