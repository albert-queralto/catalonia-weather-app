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