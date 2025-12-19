from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "catalunya_weather",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Basic settings; adjust as needed
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
)

# Periodic tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    "refresh-radar-timestamps-every-5-min": {
        "task": "app.workers.tasks.refresh_radar_timestamps",
        "schedule": 300.0,
    },
    "refresh-alerts-every-5-min": {
        "task": "app.workers.tasks.refresh_alerts",
        "schedule": 300.0,
    },
    "sync-meteocat-comarca-forecasts-hourly": {
        "task": "app.workers.tasks.sync_meteocat_comarca_forecasts",
        "schedule": 3600.0,
    },
    "evaluate-notification-rules-every-5-min": {
        "task": "app.workers.tasks.evaluate_notification_rules",
        "schedule": 300.0,
    },
}
