"""init

Revision ID: 0001_init
Revises: 
Create Date: 2025-12-18

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from geoalchemy2.types import Geometry


# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "favorite_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_favorite_locations_user_id", "favorite_locations", ["user_id"], unique=False)

    op.create_table(
        "notification_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("rule_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notification_rules_user_id", "notification_rules", ["user_id"], unique=False)

    op.create_table(
        "notification_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("notification_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
    )
    op.create_index("ix_notification_events_rule_id", "notification_events", ["rule_id"], unique=False)
    op.create_index("ix_notification_events_user_id", "notification_events", ["user_id"], unique=False)

    op.create_table(
        "comarcas",
        sa.Column("code", sa.String(length=16), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("geom", Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=False),
    )
    op.create_index("ix_comarcas_name", "comarcas", ["name"], unique=False)
    op.create_index("ix_comarcas_geom", "comarcas", ["geom"], unique=False, postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("ix_comarcas_geom", table_name="comarcas")
    op.drop_index("ix_comarcas_name", table_name="comarcas")
    op.drop_table("comarcas")

    op.drop_index("ix_notification_events_user_id", table_name="notification_events")
    op.drop_index("ix_notification_events_rule_id", table_name="notification_events")
    op.drop_table("notification_events")

    op.drop_index("ix_notification_rules_user_id", table_name="notification_rules")
    op.drop_table("notification_rules")

    op.drop_index("ix_favorite_locations_user_id", table_name="favorite_locations")
    op.drop_table("favorite_locations")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
