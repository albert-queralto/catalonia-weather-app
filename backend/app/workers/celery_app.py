from __future__ import annotations

from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "catalunya_weather",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

import app.workers.tasks  # noqa: F401

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
    "deactivate-inactive-users-daily": {
        "task": "app.workers.tasks.deactivate_inactive_users",
        "schedule": crontab(hour=0, minute=0),  # every day at midnight
        "args": (90,),  # deactivate users inactive for 90 days
    },
    'retrain-weekly': {
        'task': 'app.workers.tasks.retrain_recommender_model',
        'schedule': crontab(day_of_week=1, hour=2, minute=0),  # Monday 2 AM
    },
    "capture-station-forecast-snapshots-every-6-hours": {
        "task": "app.workers.tasks.capture_station_forecast_snapshots",
        "schedule": crontab(minute=0, hour="*/6"),
        "args": (None,),
    },
    "update-meteocat-station-data-daily": {
        "task": "app.workers.tasks.update_meteocat_station_data",
        "schedule": crontab(hour=2, minute=15),  # every day at 02:15 UTC
        "kwargs": {"days": 1},
    },
    # "refresh-radar-timestamps-every-5-min": {
    #     "task": "app.workers.tasks.refresh_radar_timestamps",
    #     "schedule": 300.0,
    # },
    # "refresh-alerts-every-5-min": {
    #     "task": "app.workers.tasks.refresh_alerts",
    #     "schedule": 300.0,
    # },
    # "sync-meteocat-comarca-forecasts-hourly": {
    #     "task": "app.workers.tasks.sync_meteocat_comarca_forecasts",
    #     "schedule": 3600.0,
    # },
    # "evaluate-notification-rules-every-5-min": {
    #     "task": "app.workers.tasks.evaluate_notification_rules",
    #     "schedule": 300.0,
    # },
    # "train-all-station-models-weekly": {
    #     "task": "app.workers.tasks.train_all_station_models",
    #     "schedule": 300.0#crontab(hour=21, minute=0, day_of_week="sat"),  # every Saturday at 03:00 UTC
    # },
}
