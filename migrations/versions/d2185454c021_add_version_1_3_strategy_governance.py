"""add version 1.3 strategy governance

Revision ID: d2185454c021
Revises: 12389f5d58a5
Create Date: 2026-08-13 18:44:10.555713
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d2185454c021"
down_revision: str | Sequence[str] | None = "12389f5d58a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    # Add strategy_key as nullable first so existing rows do not fail.
    op.add_column(
        "trade_proposals",
        sa.Column(
            "strategy_key",
            sa.String(length=128),
            nullable=True,
        ),
    )

    # Backfill existing Version 1.2 proposals.
    op.execute(
        """
        UPDATE trade_proposals
        SET strategy_key = 'default'
        WHERE strategy_key IS NULL
        """
    )

    # Now enforce NOT NULL.
    op.alter_column(
        "trade_proposals",
        "strategy_key",
        existing_type=sa.String(length=128),
        nullable=False,
    )

    # Add the index expected by the model.
    op.create_index(
        op.f("ix_trade_proposals_strategy_key"),
        "trade_proposals",
        ["strategy_key"],
        unique=False,
    )

    # Orders may exist without a strategy, so this remains nullable.
    op.add_column(
        "orders",
        sa.Column(
            "strategy_key",
            sa.String(length=128),
            nullable=True,
        ),
    )

    op.create_index(
        op.f("ix_orders_strategy_key"),
        "orders",
        ["strategy_key"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        op.f("ix_orders_strategy_key"),
        table_name="orders",
    )

    op.drop_column(
        "orders",
        "strategy_key",
    )

    op.drop_index(
        op.f("ix_trade_proposals_strategy_key"),
        table_name="trade_proposals",
    )

    op.drop_column(
        "trade_proposals",
        "strategy_key",
    )
