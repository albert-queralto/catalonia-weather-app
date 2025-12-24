"""Add cloud_cover and precipitation to events

Revision ID: 235f52e6f362
Revises: 4b94405416a5
Create Date: 2025-12-24 10:09:18.341193

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '235f52e6f362'
down_revision: Union[str, Sequence[str], None] = '4b94405416a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('events', sa.Column('cloud_cover', sa.Float(), nullable=True))
    op.add_column('events', sa.Column('precipitation', sa.Float(), nullable=True))

def downgrade():
    op.drop_column('events', 'cloud_cover')
    op.drop_column('events', 'precipitation')
