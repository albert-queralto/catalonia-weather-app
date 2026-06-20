"""Add station analytics indexes

Revision ID: b91c3f30c9a1
Revises: b71f2c0a7d2a
Create Date: 2026-06-20

"""

from typing import Sequence, Union

from alembic import op


revision: str = "b91c3f30c9a1"
down_revision: Union[str, Sequence[str], None] = "b71f2c0a7d2a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_station_measurements_station_date",
        "station_measurements",
        ["codi_estacio", "date"],
        unique=False,
    )

    op.create_index(
        "idx_station_variable_values_variable_data",
        "station_variable_values",
        ["codi_variable", "data"],
        unique=False,
    )

    op.create_index(
        "idx_station_variable_values_measurement_variable",
        "station_variable_values",
        ["measurement_id", "codi_variable"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_station_variable_values_measurement_variable", table_name="station_variable_values")
    op.drop_index("idx_station_variable_values_variable_data", table_name="station_variable_values")
    op.drop_index("idx_station_measurements_station_date", table_name="station_measurements")