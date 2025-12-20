from __future__ import annotations

import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StationMeasurement
from app.workers.celery_app import celery_app
from app.services.alerts.service import alerts_service
from app.services.radar.service import radar_service
from app.services.geo.service import comarca_service
from app.services.ml.train import train_and_save_model, fetch_all_stations
from app.db.session import session_scope


@celery_app.task
async def train_all_station_models():
    stations = fetch_all_stations()
    for st in stations:
        station_code = st["codi"]
        date_from, date_to = await get_station_date_range(station_code)
        async with session_scope() as session:
            await train_and_save_model(
                station_code, date_from, date_to, "Precipitation", "xgboost", session
            )
            
async def get_station_date_range(station_code: str, session: AsyncSession):
    stmt = (
        select(func.min(StationMeasurement.date), func.max(StationMeasurement.date))
        .where(StationMeasurement.codi_estacio == station_code)
    )
    result = await session.execute(stmt)
    min_date, max_date = result.one_or_none() or (None, None)
    # Return as strings in "YYYY-MM-DD" format if not None
    min_str = min_date.strftime("%Y-%m-%d") if min_date else None
    max_str = max_date.strftime("%Y-%m-%d") if max_date else None
    return min_str, max_str