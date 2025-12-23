"""events training context

Revision ID: 3d587a7bc29e
Revises: 825d7137537a
Create Date: 2025-12-22 19:03:48.432558

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3d587a7bc29e'
down_revision: Union[str, Sequence[str], None] = '825d7137537a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("events", sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("events", sa.Column("position", sa.Integer(), nullable=True))

    op.add_column("events", sa.Column("user_lat", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("user_lon", sa.Float(), nullable=True))

    op.add_column("events", sa.Column("weather_temp_c", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("weather_precip_prob", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("weather_wind_kmh", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("weather_is_day", sa.Float(), nullable=True))

    op.create_index("idx_events_request_id", "events", ["request_id"])
    op.create_index("idx_events_user_activity_ts", "events", ["user_id", "activity_id", "ts"])

def downgrade():
    op.drop_index("idx_events_user_activity_ts", table_name="events")
    op.drop_index("idx_events_request_id", table_name="events")

    op.drop_column("events", "weather_is_day")
    op.drop_column("events", "weather_wind_kmh")
    op.drop_column("events", "weather_precip_prob")
    op.drop_column("events", "weather_temp_c")
    op.drop_column("events", "user_lon")
    op.drop_column("events", "user_lat")
    op.drop_column("events", "position")
    op.drop_column("events", "request_id")