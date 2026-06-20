from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

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


class ForecastSnapshot(Base):
    __tablename__ = "forecast_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String, nullable=False)
    station_code = Column(String, nullable=False)
    latitud = Column(Float, nullable=False)
    longitud = Column(Float, nullable=False)
    created_at = Column(DateTime, nullable=False)


class ForecastHourly(Base):
    __tablename__ = "forecast_hourly"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("forecast_snapshots.id"), nullable=False)

    target_time = Column(DateTime, nullable=False)

    temperature_c = Column(Float, nullable=True)
    precipitation_mm = Column(Float, nullable=True)
    precipitation_probability = Column(Float, nullable=True)
    wind_speed_kmh = Column(Float, nullable=True)