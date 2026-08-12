"""add version 1.1 broker order lifecycle

Revision ID: a6eadd8735d9
Revises: 1b61c26490b5
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "a6eadd8735d9"
down_revision: str | None = "1b61c26490b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column(
            "broker_order_id",
            sa.String(length=128),
            nullable=True,
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "broker_name",
            sa.String(length=64),
            nullable=True,
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "remaining_quantity",
            sa.Float(),
            nullable=True,
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "cancelled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "orders",
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE orders
        SET remaining_quantity =
            GREATEST(
                quantity
                - COALESCE(
                    filled_quantity,
                    0
                ),
                0
            )
        """
    )

    op.alter_column(
        "orders",
        "remaining_quantity",
        existing_type=sa.Float(),
        nullable=False,
    )

    op.create_index(
        op.f("ix_orders_broker_order_id"),
        "orders",
        [
            "broker_order_id",
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_orders_broker_order_id"),
        table_name="orders",
    )

    op.drop_column(
        "orders",
        "last_synced_at",
    )

    op.drop_column(
        "orders",
        "cancelled_at",
    )

    op.drop_column(
        "orders",
        "submitted_at",
    )

    op.drop_column(
        "orders",
        "remaining_quantity",
    )

    op.drop_column(
        "orders",
        "broker_name",
    )

    op.drop_column(
        "orders",
        "broker_order_id",
    )
