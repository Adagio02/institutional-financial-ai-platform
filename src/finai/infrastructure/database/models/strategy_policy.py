from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
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


class StrategyPolicyModel(Base):
    __tablename__ = "strategy_policies"

    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "strategy_key",
            name=("uq_strategy_policies_account_strategy"),
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

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    allow_buy: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    allow_sell: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    capital_budget_fraction: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    maximum_single_proposal_fraction: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    maximum_gross_exposure_fraction: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    maximum_symbol_fraction: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    maximum_daily_loss: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    cooldown_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    maximum_active_proposals: Mapped[int] = mapped_column(
        Integer,
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
