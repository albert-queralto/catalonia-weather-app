from __future__ import annotations

from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import Column, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, JSON, LargeBinary, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    # Keep timezone-aware timestamps at the DB boundary; sqlalchemy will store as tz-aware where supported.
    return datetime.now(timezone.utc)


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


class MeteocatStation(Base):
    __tablename__ = "meteocat_stations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codi = Column(String, unique=True, nullable=False)
    nom = Column(String)
    tipus = Column(String)
    latitud = Column(Float)
    longitud = Column(Float)
    emplacament = Column(String)
    altitud = Column(Integer)
    municipi = Column(JSON)
    comarca = Column(JSON)
    provincia = Column(JSON)
    xarxa = Column(JSON)
    estats = Column(JSON)
    

class StationMeasurement(Base):
    __tablename__ = "station_measurements"
    id = Column(Integer, primary_key=True, autoincrement=True)
    codi_estacio = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    variable_values = relationship("StationVariableValue", back_populates="measurement")

class StationVariable(Base):
    __tablename__ = "station_variables"
    id = Column(Integer, primary_key=True, autoincrement=True)
    codi = Column(Integer, unique=True, nullable=False)
    nom = Column(String, nullable=False)
    unitat = Column(String, nullable=False)
    acronim = Column(String, nullable=False)
    tipus = Column(String, nullable=False)
    decimals = Column(Integer, nullable=False)
    estats = Column(JSON, nullable=False)
    bases_temporals = Column(JSON, nullable=False)
    variable_values = relationship("StationVariableValue", back_populates="variable")

class StationVariableValue(Base):
    __tablename__ = "station_variable_values"
    id = Column(Integer, primary_key=True, autoincrement=True)
    measurement_id = Column(Integer, ForeignKey("station_measurements.id"), nullable=False)
    codi_variable = Column(Integer, ForeignKey("station_variables.codi"), nullable=False)
    valor = Column(Float, nullable=False)
    data = Column(DateTime, nullable=True)
    measurement = relationship("StationMeasurement", back_populates="variable_values")
    variable = relationship("StationVariable", back_populates="variable_values")
    

class MLModel(Base):
    __tablename__ = "ml_models"
    id = Column(Integer, primary_key=True)
    station_code = Column(String, nullable=False)
    model_name = Column(String, nullable=False)
    trained_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    model = Column(LargeBinary, nullable=False)

    __table_args__ = (UniqueConstraint("station_code", "model_name", name="uq_station_model"),)