"""Seed initial admin user

Revision ID: 825d7137537a
Revises: ce0714571fe9
Create Date: 2025-12-20 19:29:33.398945

"""
from alembic import op
import sqlalchemy as sa
import os
from typing import Sequence, Union
from app.core.security import hash_password

revision: str = "825d7137537a"
down_revision: Union[str, Sequence[str], None] = "ce0714571fe9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    
    email = os.environ.get("SEED_ADMIN_EMAIL")
    password = os.environ.get("SEED_ADMIN_PASSWORD")

    # If not provided, do nothing (safer than hardcoding).
    if not email or not password:
        return

    conn = op.get_bind()

    # Idempotent: only insert if missing
    existing = conn.execute(
        sa.text("SELECT 1 FROM users WHERE email = :email"),
        {"email": email},
    ).fetchone()

    if existing:
        conn.execute(
            sa.text("UPDATE users SET role = 'admin' WHERE email = :email"),
            {"email": email},
        )
        return

    conn.execute(
        sa.text("""
            INSERT INTO users (id, email, password_hash, role, is_active)
            VALUES (gen_random_uuid(), :email, :ph, 'admin', true)
        """),
        {"email": email, "ph": hash_password(password)},
    )

def downgrade():
    email = os.environ.get("SEED_ADMIN_EMAIL")
    if not email:
        return
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM users WHERE email = :email"), {"email": email})
