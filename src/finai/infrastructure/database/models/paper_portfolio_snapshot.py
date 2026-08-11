from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import (
    UUID as PostgreSQLUUID,
)
from sqlalchemy.orm import Mapped, mapped_column

from finai.infrastructure.database.engine import Base


class PaperPortfolioSnapshotModel(Base):
    __tablename__ = "paper_portfolio_snapshots"

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

    cash: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    gross_exposure: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    net_exposure: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    equity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    realized_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    unrealized_pnl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
