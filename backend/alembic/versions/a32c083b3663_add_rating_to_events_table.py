"""Add rating to events table

Revision ID: a32c083b3663
Revises: 602ae8f78403
Create Date: 2026-02-09 17:15:53.291127

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a32c083b3663'
down_revision: Union[str, Sequence[str], None] = '602ae8f78403'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('events', sa.Column('rating', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('events', 'rating')
