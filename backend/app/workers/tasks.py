import asyncio
import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.db.session import SessionLocal, get_session
from app.db.models import MeteocatStation, User
from app.workers.celery_app import celery_app
from app.services.providers.meteocat import meteocat_client
from sqlalchemy import select

CATALONIA_TZ = ZoneInfo("Europe/Madrid")


def _run_station_model_training(
    *,
    target_variable: str = "Precipitation",
    model_name: str = "xgboost",
    station_codes: list[str] | None = None,
    station_limit: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    task: Any | None = None,
) -> dict[str, Any]:
    from app.services.ml import train_station_models_batch

    def publish_progress(meta: dict[str, Any]) -> None:
        if task is not None:
            try:
                task.update_state(state="PROGRESS", meta=meta)
            except Exception:
                pass

    with SessionLocal() as db:
        return train_station_models_batch(
            db,
            target_variable=target_variable,
            model_name=model_name,
            station_codes=station_codes,
            station_limit=station_limit,
            date_from=date_from,
            date_to=date_to,
            progress_callback=publish_progress,
        )


@celery_app.task(bind=True, name="app.workers.tasks.train_station_models")
def train_station_models(
    self,
    target_variable: str = "Precipitation",
    model_name: str = "xgboost",
    station_codes: list[str] | None = None,
    station_limit: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """
    Train and save station machine learning models in the Celery worker.

    If station_codes is omitted, all known Meteocat stations are trained. If
    dates are omitted, each station uses the available range for target_variable.
    """
    return _run_station_model_training(
        target_variable=target_variable,
        model_name=model_name,
        station_codes=station_codes,
        station_limit=station_limit,
        date_from=date_from,
        date_to=date_to,
        task=self,
    )


@celery_app.task(bind=True, name="app.workers.tasks.train_all_station_models")
def train_all_station_models(
    self,
    target_variable: str = "Precipitation",
    model_name: str = "xgboost",
    station_limit: int | None = None,
) -> dict[str, Any]:
    """Backward-compatible task name for training all station models."""
    return _run_station_model_training(
        target_variable=target_variable,
        model_name=model_name,
        station_limit=station_limit,
        task=self,
    )


def _recent_completed_dates(now: datetime, days: int) -> list[date]:
    """Return the latest completed Catalonia calendar dates before now."""
    end_date = now.astimezone(CATALONIA_TZ).date()
    current = end_date - timedelta(days=days)
    dates: list[date] = []

    while current < end_date:
        dates.append(current)
        current += timedelta(days=1)

    return dates


@celery_app.task
def update_meteocat_station_data(days: int = 1, station_limit: int | None = None):
    """
    Refresh Meteocat measured variable values for all known stations.

    By default, this updates the latest completed one-day Catalonia period based on
    datetime.now(CATALONIA_TZ).
    """
    if days <= 0:
        raise ValueError("days must be greater than 0")
    if station_limit is not None and station_limit <= 0:
        raise ValueError("station_limit must be greater than 0")

    async def run():
        period_end = datetime.now(CATALONIA_TZ)
        period_start = period_end - timedelta(days=days)
        dates_to_fetch = _recent_completed_dates(period_end, days)

        with SessionLocal() as db:
            stmt = select(MeteocatStation.codi).order_by(MeteocatStation.codi)
            if station_limit is not None:
                stmt = stmt.limit(station_limit)
            station_codes = list(db.execute(stmt).scalars().all())

        failures = []
        updated_station_days = 0

        for station_code in station_codes:
            for target_date in dates_to_fetch:
                try:
                    await meteocat_client.fetch_and_store_station_variable_values(
                        station_code,
                        target_date.year,
                        target_date.month,
                        target_date.day,
                    )
                    updated_station_days += 1
                except Exception as exc:
                    failures.append(
                        {
                            "station_code": station_code,
                            "date": target_date.isoformat(),
                            "error": str(exc),
                        }
                    )

        status = "ok"
        if failures:
            status = "failed" if updated_station_days == 0 else "partial"
        elif not station_codes:
            status = "no_stations"

        return {
            "status": status,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "days": days,
            "dates": [target_date.isoformat() for target_date in dates_to_fetch],
            "stations": len(station_codes),
            "updated_station_days": updated_station_days,
            "failed_station_days": len(failures),
            "failures": failures[:25],
        }

    return asyncio.run(run())


@celery_app.task
def deactivate_inactive_users(days: int = 90):
    """
    Celery task to deactivate users who have not logged in for a specified number of days.

    Args:
        days (int, optional): Number of days of inactivity before deactivation. Defaults to 90.

    This task sets 'is_active' to False for all regular users ('user' role) whose
    last login was before the threshold date.
    """
    db = next(get_session())
    threshold = datetime.now(timezone.utc) - timedelta(days=days)
    inactive_users = db.query(User).filter(
        User.last_login < threshold,
        User.is_active == True,
        User.role == "user"
    ).all()
    for user in inactive_users:
        user.is_active = False
    db.commit()
    
@celery_app.task
def delete_unverified_users(days: int = 1):
    """
    Celery task to delete users who have not verified their email within a specified number of days.

    Args:
        days (int, optional): Number of days since registration before deletion. Defaults to 1.

    This task deletes all users whose 'is_verified' is False and whose 'created_at' is older than the threshold date.
    """
    db = next(get_session())
    threshold = datetime.now(timezone.utc) - timedelta(days=days)
    unverified_users = db.query(User).filter(
        User.is_verified == False,
        User.created_at < threshold
    ).all()
    for user in unverified_users:
        db.delete(user)
    db.commit()

@celery_app.task
def retrain_recommender_model():
    """Retrain model weekly with fresh data"""
    model_path = Path(settings.model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    new_model_path = model_path.with_name(f"{model_path.stem}_new{model_path.suffix}")

    env = os.environ.copy()
    database_url = env.get("DATABASE_URL") or settings.database_url
    env["DATABASE_URL"] = database_url.replace("+asyncpg", "+psycopg2")
    env["MODEL_OUT"] = str(new_model_path)
    env.setdefault("LOOKBACK_DAYS", "60")

    result = subprocess.run(
        [sys.executable, "-m", "app.services.recommender.train_from_db"],
        env=env,
        capture_output=True,
        text=True,
    )
    
    if result.returncode == 0:
        new_model_path.replace(model_path)
        return {
            "status": "success",
            "model_path": str(model_path),
            "output": result.stdout,
        }

    return {
        "status": "failed",
        "returncode": result.returncode,
        "error": result.stderr,
        "output": result.stdout,
    }
    
@celery_app.task
def capture_station_forecast_snapshots(limit: int | None = None):
    """
    Store Open-Meteo forecasts for Meteocat station locations.
    Run this every 6 or 12 hours so forecast accuracy can be calculated later.
    """
    from app.db.session import SessionLocal
    from app.services.station_analytics.forecast_accuracy import (
        capture_openmeteo_forecasts_for_all_stations,
    )

    async def run():
        with SessionLocal() as db:
            return await capture_openmeteo_forecasts_for_all_stations(db, limit=limit)

    return asyncio.run(run())
