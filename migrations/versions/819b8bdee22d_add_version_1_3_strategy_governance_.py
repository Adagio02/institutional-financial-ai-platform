"""add version 1.3 strategy governance tables

Revision ID: 819b8bdee22d
Revises: d2185454c021
Create Date: 2026-08-13 20:09:37.525402
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "819b8bdee22d"
down_revision: str | Sequence[str] | None = "d2185454c021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create Version 1.3 strategy governance tables."""

    # ---------------------------------------------------------
    # Strategy policies
    # ---------------------------------------------------------

    op.create_table(
        "strategy_policies",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "strategy_key",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "allow_buy",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "allow_sell",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "capital_budget_fraction",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "maximum_single_proposal_fraction",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "maximum_gross_exposure_fraction",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "maximum_symbol_fraction",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "maximum_daily_loss",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "cooldown_seconds",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "maximum_active_proposals",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["paper_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "strategy_key",
            name="uq_strategy_policies_account_strategy",
        ),
    )

    op.create_index(
        op.f("ix_strategy_policies_account_id"),
        "strategy_policies",
        ["account_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_strategy_policies_strategy_key"),
        "strategy_policies",
        ["strategy_key"],
        unique=False,
    )

    # ---------------------------------------------------------
    # Strategy positions
    # ---------------------------------------------------------

    op.create_table(
        "strategy_positions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "strategy_key",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "instrument_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "symbol",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "quantity",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "average_price",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "realized_pnl",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["paper_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["instruments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "strategy_key",
            "instrument_id",
            name="uq_strategy_positions_identity",
        ),
    )

    op.create_index(
        op.f("ix_strategy_positions_account_id"),
        "strategy_positions",
        ["account_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_strategy_positions_strategy_key"),
        "strategy_positions",
        ["strategy_key"],
        unique=False,
    )

    op.create_index(
        op.f("ix_strategy_positions_instrument_id"),
        "strategy_positions",
        ["instrument_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_strategy_positions_symbol"),
        "strategy_positions",
        ["symbol"],
        unique=False,
    )

    # ---------------------------------------------------------
    # Strategy attribution events
    # ---------------------------------------------------------

    op.create_table(
        "strategy_attribution_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "strategy_key",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "instrument_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "order_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "fill_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "symbol",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "notional",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "realized_pnl_delta",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "commission",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "net_pnl_delta",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["paper_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["instruments.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["fill_id"],
            ["execution_fills.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f(
            "ix_strategy_attribution_events_account_id"
        ),
        "strategy_attribution_events",
        ["account_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_strategy_attribution_events_strategy_key"
        ),
        "strategy_attribution_events",
        ["strategy_key"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_strategy_attribution_events_order_id"
        ),
        "strategy_attribution_events",
        ["order_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_strategy_attribution_events_created_at"
        ),
        "strategy_attribution_events",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove Version 1.3 strategy governance tables."""

    # Attribution events first because they depend on other tables.

    op.drop_index(
        op.f(
            "ix_strategy_attribution_events_created_at"
        ),
        table_name="strategy_attribution_events",
    )

    op.drop_index(
        op.f(
            "ix_strategy_attribution_events_order_id"
        ),
        table_name="strategy_attribution_events",
    )

    op.drop_index(
        op.f(
            "ix_strategy_attribution_events_strategy_key"
        ),
        table_name="strategy_attribution_events",
    )

    op.drop_index(
        op.f(
            "ix_strategy_attribution_events_account_id"
        ),
        table_name="strategy_attribution_events",
    )

    op.drop_table("strategy_attribution_events")

    # Strategy positions.

    op.drop_index(
        op.f("ix_strategy_positions_symbol"),
        table_name="strategy_positions",
    )

    op.drop_index(
        op.f("ix_strategy_positions_instrument_id"),
        table_name="strategy_positions",
    )

    op.drop_index(
        op.f("ix_strategy_positions_strategy_key"),
        table_name="strategy_positions",
    )

    op.drop_index(
        op.f("ix_strategy_positions_account_id"),
        table_name="strategy_positions",
    )

    op.drop_table("strategy_positions")

    # Strategy policies.

    op.drop_index(
        op.f("ix_strategy_policies_strategy_key"),
        table_name="strategy_policies",
    )

    op.drop_index(
        op.f("ix_strategy_policies_account_id"),
        table_name="strategy_policies",
    )

    op.drop_table("strategy_policies")