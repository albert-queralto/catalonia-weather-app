import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, ARRAY, func, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography
from app.db.base import Base
from datetime import datetime, timezone

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")  # "user" | "admin"
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notification_preferences = Column(Boolean, nullable=False, default=True)
    favorite_comarques = Column(ARRAY(String), nullable=False, default=[])
    last_login = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

class UserPreference(Base):
    __tablename__ = "user_preferences"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    category = Column(String, primary_key=True)
    weight = Column(Integer, nullable=False, default=1)