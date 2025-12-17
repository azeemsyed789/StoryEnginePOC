"""merge heads

Revision ID: c0e18effd64a
Revises: 82fe01bfd68e, allow_multiple_story_designs
Create Date: 2025-12-16 19:51:35.338380

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0e18effd64a'
down_revision: Union[str, Sequence[str], None] = ('82fe01bfd68e', 'allow_multiple_story_designs')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
