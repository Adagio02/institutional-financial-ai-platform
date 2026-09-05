"""merge migration heads for v2.1

Revision ID: da5bb6ef279a
Revises: 3acf2692fc4f, e8023e1b191f
Create Date: 2026-08-23 14:05:59.853143

"""

from collections.abc import Sequence




# revision identifiers, used by Alembic.
revision: str = 'da5bb6ef279a'
down_revision: str | Sequence[str] | None = ('3acf2692fc4f', 'e8023e1b191f')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass