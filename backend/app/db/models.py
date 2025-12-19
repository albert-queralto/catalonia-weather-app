from __future__ import annotations

from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    # Keep timezone-aware timestamps at the DB boundary; sqlalchemy will store as tz-aware where supported.
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    favorites: Mapped[list["FavoriteLocation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    rules: Mapped[list["NotificationRule"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class FavoriteLocation(Base):
    __tablename__ = "favorite_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    name: Mapped[str] = mapped_column(String(255))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="favorites")


class NotificationRule(Base):
    __tablename__ = "notification_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    name: Mapped[str] = mapped_column(String(255))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # JSON text so rules can evolve without schema churn.
    # Example:
    # {"metric":"wind_gust_m_s","op":">=","threshold":20,"location":{"lat":41.3,"lon":2.1},"cooldown_seconds":1800}
    rule_json: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="rules")
    events: Mapped[list["NotificationEvent"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )


class NotificationEvent(Base):
    __tablename__ = "notification_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("notification_rules.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    fired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Store a compact JSON blob of what triggered the event (metric, value, threshold, coordinates, etc.)
    payload_json: Mapped[str] = mapped_column(Text)

    rule: Mapped[NotificationRule] = relationship(back_populates="events")


class Comarca(Base):
    __tablename__ = "comarcas"

    # Official comarca code (e.g., "BAR", "VLL" etc.). Primary key for stable joins.
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)

    # PostGIS geometry (WGS84).
    geom: Mapped[str] = mapped_column(Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=True))
