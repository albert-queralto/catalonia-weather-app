import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, ARRAY, func, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")  # "user" | "admin"
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class UserPreference(Base):
    __tablename__ = "user_preferences"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    category = Column(String, primary_key=True)
    weight = Column(Integer, nullable=False, default=1)

class Activity(Base):
    __tablename__ = "activities"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    tags = Column(ARRAY(String), nullable=False, default=list)
    indoor = Column(Boolean, nullable=False, default=False)
    covered = Column(Boolean, nullable=False, default=False)
    price_level = Column(Integer, nullable=False, default=0)
    difficulty = Column(Integer, nullable=False, default=0)
    duration_minutes = Column(Integer, nullable=False, default=60)
    location = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Event(Base):
    __tablename__ = "events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    activity_id = Column(UUID(as_uuid=True), ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String, nullable=False)
    ts = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    request_id = Column(UUID(as_uuid=True), nullable=True)
    position = Column(Integer, nullable=True)
    
    user_lat = Column(Float, nullable=True)
    user_lon = Column(Float, nullable=True)
    
    weather_temp_c = Column(Float, nullable=True)
    weather_precip_prob = Column(Float, nullable=True)
    weather_wind_kmh = Column(Float, nullable=True)
    weather_is_day = Column(Float, nullable=True)