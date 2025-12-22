from app.db.session import SessionLocal
from app.db.models import StationMeasurement
from app.workers.celery_app import celery_app
from app.services.ml.train import train_and_save_model, fetch_all_stations
from sqlalchemy import select, func

@celery_app.task
def train_all_station_models():
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
    stmt = (
        select(func.min(StationMeasurement.date), func.max(StationMeasurement.date))
        .where(StationMeasurement.codi_estacio == station_code)
    )
    result = db.execute(stmt)
    min_date, max_date = result.one_or_none() or (None, None)
    min_str = min_date.strftime("%Y-%m-%d") if min_date else None
    max_str = max_date.strftime("%Y-%m-%d") if max_date else None
    return min_str, max_str