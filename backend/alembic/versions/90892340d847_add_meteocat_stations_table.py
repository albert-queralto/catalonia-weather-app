"""Add meteocat_stations table

Revision ID: 90892340d847
Revises: 0001_init
Create Date: 2025-12-19 14:34:48.071417

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '90892340d847'
down_revision: Union[str, Sequence[str], None] = '0001_init'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'meteocat_stations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('codi', sa.String(), unique=True, nullable=False),
        sa.Column('nom', sa.String()),
        sa.Column('tipus', sa.String()),
        sa.Column('latitud', sa.Float()),
        sa.Column('longitud', sa.Float()),
        sa.Column('emplacament', sa.String()),
        sa.Column('altitud', sa.Integer()),
        sa.Column('municipi', sa.JSON()),
        sa.Column('comarca', sa.JSON()),
        sa.Column('provincia', sa.JSON()),
        sa.Column('xarxa', sa.JSON()),
        sa.Column('estats', sa.JSON()),
    )


def downgrade():
    op.drop_table('meteocat_stations')
