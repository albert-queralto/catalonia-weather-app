from app.db.session import SessionLocal, get_session
from app.db.models import StationMeasurement, User
from app.workers.celery_app import celery_app
from app.services.ml.train import train_and_save_model, fetch_all_stations
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta


@celery_app.task
def train_all_station_models():
    """
    Celery task to train and save machine learning models for all weather stations.

    For each station, determines the available date range of measurements and
    trains a precipitation prediction model using XGBoost, saving the model to disk.
    """
    stations = fetch_all_stations()
    db = SessionLocal()
    try:
        for st in stations:
            station_code = st["codi"]
            date_from, date_to = get_station_date_range(station_code, db)
            if not date_from or not date_to:
                continue
            train_and_save_model(
                station_code, date_from, date_to, "Precipitació", "xgboost", db
            )
    finally:
        db.close()

def get_station_date_range(station_code: str, db):
    """
    Get the minimum and maximum measurement dates for a given station.

    Args:
        station_code (str): The code of the weather station.
        db: SQLAlchemy database session.

    Returns:
        tuple[str | None, str | None]: (min_date, max_date) as 'YYYY-MM-DD' strings,
        or (None, None) if no data is found.
    """
    stmt = (
        select(func.min(StationMeasurement.date), func.max(StationMeasurement.date))
        .where(StationMeasurement.codi_estacio == station_code)
    )
    result = db.execute(stmt)
    min_date, max_date = result.one_or_none() or (None, None)
    min_str = min_date.strftime("%Y-%m-%d") if min_date else None
    max_str = max_date.strftime("%Y-%m-%d") if max_date else None
    return min_str, max_str

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
