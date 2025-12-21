from __future__ import annotations

from typing import Generator
from contextlib import contextmanager

from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine

from app.core.config import settings

# Sync engine/session for all usage
engine = create_engine(settings.database_url.replace("+asyncpg", ""), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)

# Sync session scope (for all usage)
@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# FastAPI dependency for sync session
def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session