"""Add categories table

Revision ID: 4b94405416a5
Revises: af8e529e4983
Create Date: 2025-12-24 09:12:01.128679

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b94405416a5'
down_revision: Union[str, Sequence[str], None] = 'af8e529e4983'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'categories',
        sa.Column('name', sa.String(), primary_key=True, unique=True, nullable=False)
    )
    # Insert initial categories
    categories = ["Sport", "Culture", "Nature", "Food", "Leisure", "Other"]
    for cat in categories:
        op.execute(f"INSERT INTO categories (name) VALUES ('{cat}')")
    # Add the foreign key constraint after categories are present
    op.create_foreign_key(
        'fk_activities_category', 'activities', 'categories', ['category'], ['name'], ondelete="SET NULL"
    )

def downgrade():
    op.drop_constraint('fk_activities_category', 'activities', type_='foreignkey')
    op.drop_table('categories')
