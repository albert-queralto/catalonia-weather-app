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