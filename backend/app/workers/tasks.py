from __future__ import annotations

import asyncio

from app.workers.celery_app import celery_app
from app.services.alerts.service import alerts_service
from app.services.radar.service import radar_service
from app.services.geo.service import comarca_service
from app.services.ml.train import train_and_save_model, fetch_all_stations
from app.db.session import session_scope


@celery_app.task
async def train_all_station_models(date_from, date_to, target_variable="Precipitation", model_name="random_forest"):
    stations = fetch_all_stations()
    for st in stations:
        station_code = st["codi"]
        await train_and_save_model(station_code, date_from, date_to, target_variable, model_name, session)
