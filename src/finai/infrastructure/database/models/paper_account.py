from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Float,
    String,
)
from sqlalchemy.dialects.postgresql import (
    UUID as PostgreSQLUUID,
)
from sqlalchemy.orm import Mapped, mapped_column

from finai.infrastructure.database.engine import Base


class PaperAccountModel(Base):
    __tablename__ = "paper_accounts"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    base_currency: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="USD",
    )

    initial_cash: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    cash: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    realized_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
