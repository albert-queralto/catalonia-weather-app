from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import (
    MeteocatStation,
    StationMeasurement,
    StationVariable,
    StationVariableValue,
)
from app.db.session import get_session, SessionLocal
from app.services.providers.meteocat import meteocat_client
from app.services.providers.schemas import StationMeasuredData
from typing import List, Optional
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/meteocat/stations")
def get_meteocat_stations(db: Session = Depends(get_session)):
    result = db.execute(select(MeteocatStation))
    stations = result.scalars().all()
    return [s.__dict__ for s in stations]

@router.post("/meteocat/stations/populate")
async def populate_meteocat_stations(estat: str = "ope", data: str = "2017-03-27Z"):
    await meteocat_client.fetch_and_store_meteocat_stations(estat, data)
    return {"status": "ok"}

@router.get(
    "/meteocat/station-measured/{codi_estacio}/{any}/{mes}/{dia}",
    response_model=List[StationMeasuredData]
)
async def get_station_measured_data(
    codi_estacio: str,
    any: int,
    mes: int,
    dia: int,
):
    data = await meteocat_client.fetch_station_measured_data(codi_estacio, any, mes, dia)
    return data

@router.post("/meteocat/station/{codi_estacio}/variables/metadata/store")
async def store_station_variable_metadata(
    codi_estacio: str,
    estat: str = "ope",
    data: str = None,
):
    await meteocat_client.fetch_and_store_station_variable_metadata(codi_estacio, estat, data)
    return {"status": "ok"}

@router.post("/meteocat/station/{codi_estacio}/{any}/{mes}/{dia}/variables/store")
async def store_station_variable_values(
    codi_estacio: str,
    any: int,
    mes: int,
    dia: int,
):
    await meteocat_client.fetch_and_store_station_variable_values(codi_estacio, any, mes, dia)
    return {"status": "ok"}

@router.post("/meteocat/stations/variables/store-range")
def store_all_stations_variable_values(
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    background_tasks: BackgroundTasks = None,
):
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    db = SessionLocal()
    try:
        result = db.execute(select(MeteocatStation))
        stations = result.scalars().all()
        station_codes = [station.codi for station in stations]
    finally:
        db.close()

    async def process_all():
        for codi_estacio in station_codes:
            current_date = start_dt
            while current_date <= end_dt:
                await meteocat_client.fetch_and_store_station_variable_values(
                    codi_estacio,
                    current_date.year,
                    current_date.month,
                    current_date.day,
                )
                current_date += timedelta(days=1)

    if background_tasks is not None:
        background_tasks.add_task(process_all)
        return {"status": "processing in background"}
    else:
        process_all()
        return {"status": "ok"}
    
@router.post("/meteocat/stations/variables/metadata/store-all")
async def store_all_stations_variable_metadata_sync(
    estat: str = "ope",
    data: str = '2017-03-27Z',
):
    db = SessionLocal()
    try:
        result = db.execute(select(MeteocatStation))
        stations = result.scalars().all()
        station_codes = [station.codi for station in stations]

        for codi_estacio in station_codes:
            await meteocat_client.fetch_and_store_station_variable_metadata(
                codi_estacio, estat, data
            )
    finally:
        db.close()
    return {"status": "ok"}

@router.get("/meteocat/station/{codi_estacio}/variables/values")
def get_station_variables_and_values(
    codi_estacio: str,
    date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_session),
):
    stmt = select(StationMeasurement).where(StationMeasurement.codi_estacio == codi_estacio)
    if date:
        dt = datetime.strptime(date, "%Y-%m-%d")
        stmt = stmt.where(StationMeasurement.date == dt)
    result = db.execute(stmt)
    measurements = result.scalars().all()
    
    output = []
    for measurement in measurements:
        stmt_vars = select(StationVariableValue, StationVariable).join(
            StationVariable, StationVariableValue.codi_variable == StationVariable.codi
        ).where(StationVariableValue.measurement_id == measurement.id)
        result_vars = db.execute(stmt_vars)
        variables = [
            {
                'codi': var.codi_variable,
                'nom': meta.nom,
                'valor': var.valor,
                'unitat': meta.unitat,
                'data': var.data,
            }
            for var, meta in result_vars.all()
        ]
        output.append({
            "codi_estacio": measurement.codi_estacio,
            "date": measurement.date,
            "variables": variables,
        })
    return output

@router.get("/meteocat/station/{codi_estacio}/variables")
def get_station_variables(
    codi_estacio: str,
    db: Session = Depends(get_session),
):
    stmt = (
        select(
            StationVariable.codi,
            StationVariable.nom,
            StationVariable.unitat,
            StationVariable.acronim,
            StationVariable.tipus,
            StationVariable.decimals,
        )
        .join(StationVariableValue, StationVariable.codi == StationVariableValue.codi_variable)
        .join(StationMeasurement, StationVariableValue.measurement_id == StationMeasurement.id)
        .where(StationMeasurement.codi_estacio == codi_estacio)
        .distinct()
    )
    result = db.execute(stmt)
    variables = result.all()
    return [
        {
            "codi": v.codi,
            "nom": v.nom,
            "unitat": v.unitat,
            "acronim": v.acronim,
            "tipus": v.tipus,
            "decimals": v.decimals,
        }
        for v in variables
    ]
    
@router.get("/meteocat/station/{codi_estacio}/variable/{codi_variable}/values")
def get_all_values_for_station_variable(
    codi_estacio: str,
    codi_variable: int,
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    db: Session = Depends(get_session),
):
    stmt = (
        select(
            StationMeasurement.date,
            StationVariableValue.valor,
            StationVariableValue.data
        )
        .join(StationVariableValue, StationMeasurement.id == StationVariableValue.measurement_id)
        .where(
            StationMeasurement.codi_estacio == codi_estacio,
            StationVariableValue.codi_variable == codi_variable
        )
    )
    if date_from:
        dt_from = datetime.strptime(date_from, "%Y-%m-%d")
        stmt = stmt.where(StationMeasurement.date >= dt_from)
    if date_to:
        dt_to = datetime.strptime(date_to, "%Y-%m-%d")
        stmt = stmt.where(StationMeasurement.date <= dt_to)
    stmt = stmt.order_by(StationMeasurement.date, StationVariableValue.data)
    result = db.execute(stmt)
    values = [
        {
            "date": row.date,
            "valor": row.valor,
            "data": row.data,
        }
        for row in result.all()
    ]
    return values