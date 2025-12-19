from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models import MeteocatStation
from app.db.session import get_session
from app.services.providers.meteocat import meteocat_client
from app.services.providers.schemas import StationMeasuredData
from typing import List
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/meteocat/stations")
async def get_meteocat_stations(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(MeteocatStation))
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
async def store_all_stations_variable_values(
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    background_tasks: BackgroundTasks = None,
):
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")

    # Fetch all stations from the DB
    db = await anext(get_session())
    try:
        result = await db.execute(select(MeteocatStation))
        stations = result.scalars().all()
        station_codes = [station.codi for station in stations]
    finally:
        await db.close()

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
        await process_all()
        return {"status": "ok"}
    
@router.post("/meteocat/stations/variables/metadata/store-all")
async def store_all_stations_variable_metadata(
    estat: str = "ope",
    data: str = '2017-03-27Z',
):
    # Fetch all stations from the DB
    db = await anext(get_session())
    try:
        result = await db.execute(select(MeteocatStation))
        stations = result.scalars().all()
        station_codes = [station.codi for station in stations]

        for codi_estacio in station_codes:
            await meteocat_client.fetch_and_store_station_variable_metadata(
                codi_estacio, estat, data
            )
    finally:
        await db.close()
    return {"status": "ok"}