from __future__ import annotations

import asyncio

from app.workers.celery_app import celery_app
from app.services.alerts.service import alerts_service
from app.services.radar.service import radar_service
from app.services.geo.service import comarca_service
# from app.services.ml.train import 
from app.db.session import session_scope


@celery_app.task(name="app.workers.tasks.refresh_radar_timestamps")
def refresh_radar_timestamps() -> dict:
    return asyncio.run(radar_service.get_timestamps())


@celery_app.task(name="app.workers.tasks.refresh_alerts")
def refresh_alerts() -> dict:
    data = asyncio.run(alerts_service.get_alerts(bbox=None))
    return data.model_dump(mode="json")


# @celery_app.task(name="app.workers.tasks.sync_meteocat_comarca_forecasts")
# def sync_meteocat_comarca_forecasts() -> dict:
#     async def _run():
#         async with session_scope() as session:
#             comarcas = await comarca_service.list_comarcas(session=session)
#         ok = 0
#         for c in comarcas:
#             try:
#                 await forecast_service.get_comarca_forecast(comarca_code=c.code, tz="Europe/Madrid")
#                 ok += 1
#             except Exception:
#                 continue
#         return {"comarcas": len(comarcas), "cached": ok}

#     return asyncio.run(_run())
