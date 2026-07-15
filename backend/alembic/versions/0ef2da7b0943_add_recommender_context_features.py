"""add recommender context features

Revision ID: 0ef2da7b0943
Revises: c02a9d4153cd
Create Date: 2026-06-21 23:40:03.412474

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0ef2da7b0943'
down_revision: Union[str, Sequence[str], None] = 'c02a9d4153cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column("activities", sa.Column("opening_hours", postgresql.JSONB(), nullable=True))

    op.add_column("events", sa.Column("apparent_temp_c", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("uv_index", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("air_quality_score", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("air_quality_label", sa.String(), nullable=True))
    op.add_column("events", sa.Column("ozone", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("alert_severity", sa.Integer(), nullable=True))
    op.add_column("events", sa.Column("weather_condition", sa.String(), nullable=True))

    op.add_column("events", sa.Column("ranking_strategy", sa.String(), nullable=True))
    op.add_column("events", sa.Column("model_score", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("model_confidence", sa.Float(), nullable=True))
    op.add_column("events", sa.Column("exploration_bucket", sa.String(), nullable=True))

    op.add_column("events", sa.Column("dismiss_reason", sa.String(), nullable=True))

    op.create_index("idx_events_weather_condition", "events", ["weather_condition"])
    op.create_index("idx_events_ranking_strategy", "events", ["ranking_strategy"])
    op.create_index("idx_events_alert_severity", "events", ["alert_severity"])


def downgrade():
    op.drop_index("idx_events_alert_severity", table_name="events")
    op.drop_index("idx_events_ranking_strategy", table_name="events")
    op.drop_index("idx_events_weather_condition", table_name="events")

    op.drop_column("events", "dismiss_reason")
    op.drop_column("events", "exploration_bucket")
    op.drop_column("events", "model_confidence")
    op.drop_column("events", "model_score")
    op.drop_column("events", "ranking_strategy")
    op.drop_column("events", "weather_condition")
    op.drop_column("events", "alert_severity")
    op.drop_column("events", "ozone")
    op.drop_column("events", "air_quality_label")
    op.drop_column("events", "air_quality_score")
    op.drop_column("events", "uv_index")
    op.drop_column("events", "apparent_temp_c")

    op.drop_column("activities", "opening_hours")
