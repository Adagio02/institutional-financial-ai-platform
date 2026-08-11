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


class ExecutionFillModel(Base):
    __tablename__ = "execution_fills"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    order_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    quantity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    notional: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    commission: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    slippage_cost: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
