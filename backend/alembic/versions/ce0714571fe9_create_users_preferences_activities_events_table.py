"""Create Users, UserPreferences, Activities, and Events tables

Revision ID: ce0714571fe9
Revises: ef41aabc05c0
Create Date: 2025-12-20 19:29:33.398945

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from geoalchemy2 import Geography


# revision identifiers, used by Alembic.
revision: str = 'ce0714571fe9'
down_revision: Union[str, Sequence[str], None] = 'ef41aabc05c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default=sa.text("'user'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("category", sa.String(), primary_key=True),
        sa.Column("weight", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )

    op.create_table(
        "activities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("indoor", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("covered", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("price_level", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("difficulty", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default=sa.text("60")),
        sa.Column("location", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_activities_locations", "activities", ["location"], postgresql_using="gist")

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("activities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_events_user_ts", "events", ["user_id", "ts"])
    op.create_index("idx_events_activity_ts", "events", ["activity_id", "ts"])

def downgrade():
    op.drop_index("idx_events_activity_ts", table_name="events")
    op.drop_index("idx_events_user_ts", table_name="events")
    op.drop_table("events")

    op.drop_index("idx_activities_locations", table_name="activities")
    op.drop_table("activities")

    op.drop_table("user_preferences")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
