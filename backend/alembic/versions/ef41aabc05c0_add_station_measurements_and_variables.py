"""Add station measurements, variables, and variable values

Revision ID: ef41aabc05c0
Revises: 90892340d847
Create Date: 2025-12-19 15:19:04.506520

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ef41aabc05c0'
down_revision: Union[str, Sequence[str], None] = '90892340d847'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.create_table(
        'station_measurements',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('codi_estacio', sa.String(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
    )
    op.create_table(
        'station_variables',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('codi', sa.Integer(), nullable=False, unique=True),
        sa.Column('nom', sa.String(), nullable=False),
        sa.Column('unitat', sa.String(), nullable=False),
        sa.Column('acronim', sa.String(), nullable=False),
        sa.Column('tipus', sa.String(), nullable=False),
        sa.Column('decimals', sa.Integer(), nullable=False),
        sa.Column('estats', sa.JSON(), nullable=False),
        sa.Column('bases_temporals', sa.JSON(), nullable=False),
    )
    op.create_table(
        'station_variable_values',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('measurement_id', sa.Integer(), sa.ForeignKey('station_measurements.id'), nullable=False),
        sa.Column('codi_variable', sa.Integer(), sa.ForeignKey('station_variables.codi'), nullable=False),
        sa.Column('valor', sa.Float(), nullable=False),
        sa.Column('data', sa.DateTime(), nullable=True),
    )

def downgrade():
    op.drop_table('station_variable_values')
    op.drop_table('station_variables')
    op.drop_table('station_measurements')