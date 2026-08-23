"""add version 1.3 strategy governance tables

Revision ID: 3acf2692fc4f
Revises: 819b8bdee22d
Create Date: 2026-08-13 20:14:44.649509

"""

from collections.abc import Sequence



revision: str = "3acf2692fc4f"
down_revision: str | Sequence[str] | None = "d2185454c021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass