"""Create ML models table

Revision ID: ce0714571fe9
Revises: ef41aabc05c0
Create Date: 2025-12-20 19:29:33.398945

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ce0714571fe9'
down_revision: Union[str, Sequence[str], None] = 'ef41aabc05c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'ml_models',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('station_code', sa.String, nullable=False),
        sa.Column('model_name', sa.String, nullable=False),
        sa.Column('trained_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('model', sa.LargeBinary, nullable=False),
        sa.UniqueConstraint('station_code', 'model_name', name='uq_station_model')
    )

def downgrade():
    op.drop_table('ml_models')
