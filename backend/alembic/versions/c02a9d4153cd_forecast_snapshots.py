"""Add forecast snapshot tables

Revision ID: c02a9d4153cd
Revises: b91c3f30c9a1
Create Date: 2026-06-20

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c02a9d4153cd"
down_revision: Union[str, Sequence[str], None] = "b91c3f30c9a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forecast_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("station_code", sa.String(), nullable=False),
        sa.Column("latitud", sa.Float(), nullable=False),
        sa.Column("longitud", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "forecast_hourly",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("forecast_snapshots.id"), nullable=False),
        sa.Column("target_time", sa.DateTime(), nullable=False),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("precipitation_mm", sa.Float(), nullable=True),
        sa.Column("precipitation_probability", sa.Float(), nullable=True),
        sa.Column("wind_speed_kmh", sa.Float(), nullable=True),
    )

    op.create_index(
        "idx_forecast_snapshots_station_created",
        "forecast_snapshots",
        ["station_code", "created_at"],
    )

    op.create_index(
        "idx_forecast_hourly_snapshot_target",
        "forecast_hourly",
        ["snapshot_id", "target_time"],
    )

    op.create_index(
        "idx_forecast_hourly_target",
        "forecast_hourly",
        ["target_time"],
    )


def downgrade() -> None:
    op.drop_index("idx_forecast_hourly_target", table_name="forecast_hourly")
    op.drop_index("idx_forecast_hourly_snapshot_target", table_name="forecast_hourly")
    op.drop_index("idx_forecast_snapshots_station_created", table_name="forecast_snapshots")
    op.drop_table("forecast_hourly")
    op.drop_table("forecast_snapshots")