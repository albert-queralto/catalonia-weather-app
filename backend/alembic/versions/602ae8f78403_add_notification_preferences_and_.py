"""Add notification_preferences, favorite_comarques, last_login, is_verified, reset_token and verification_token to users

Revision ID: 602ae8f78403
Revises: 235f52e6f362
Create Date: 2026-02-07 09:53:04.888114

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '602ae8f78403'
down_revision: Union[str, Sequence[str], None] = '235f52e6f362'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('notification_preferences', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('users', sa.Column('favorite_comarques', sa.ARRAY(sa.String()), nullable=False, server_default='{}'))
    op.add_column('users', sa.Column('last_login', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('reset_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('verification_token', sa.String(), nullable=True))
    
    # Set is_verified True for admin user(s)
    op.execute("UPDATE users SET is_verified = TRUE WHERE role = 'admin'")

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'favorite_comarques')
    op.drop_column('users', 'notification_preferences')
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'is_verified')
    op.drop_column('users', 'reset_token')
    op.drop_column('users', 'verification_token')
