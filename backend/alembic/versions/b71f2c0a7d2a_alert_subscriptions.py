"""Add personalized alert subscription fields

Revision ID: b71f2c0a7d2a
Revises: a32c083b3663
Create Date: 2026-06-20

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b71f2c0a7d2a"
down_revision: Union[str, Sequence[str], None] = "a32c083b3663"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "alert_subscribe_current_location",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.add_column(
        "users",
        sa.Column("alert_current_comarca", sa.String(), nullable=True),
    )

    op.add_column(
        "users",
        sa.Column(
            "alert_meteor_types",
            sa.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "alert_min_severity",
            sa.Integer(),
            nullable=False,
            server_default="2",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "alert_min_severity")
    op.drop_column("users", "alert_meteor_types")
    op.drop_column("users", "alert_current_comarca")
    op.drop_column("users", "alert_subscribe_current_location")