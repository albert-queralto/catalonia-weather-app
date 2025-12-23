"""Add validated column to activities table

Revision ID: af8e529e4983
Revises: 3d587a7bc29e
Create Date: 2025-12-23 15:08:55.540640

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af8e529e4983'
down_revision: Union[str, Sequence[str], None] = '3d587a7bc29e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('activities', sa.Column('validated', sa.Boolean(), nullable=True, server_default=sa.false()))

def downgrade():
    op.drop_column('activities', 'validated')
