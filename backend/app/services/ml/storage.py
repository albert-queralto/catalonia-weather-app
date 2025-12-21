from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from app.db.models import MLModel
from datetime import datetime, timezone

def save_model_to_db_sync(station_code, model_name, model_bytes, session: Session):
    try:
        stmt = select(MLModel).where(
            MLModel.station_code == station_code,
            MLModel.model_name == model_name
        )
        result = session.execute(stmt)
        obj = result.scalars().first()
        if obj:
            obj.model = model_bytes
            obj.trained_at = datetime.now(timezone.utc)
        else:
            obj = MLModel(
                station_code=station_code,
                model_name=model_name,
                model=model_bytes,
                trained_at=datetime.now(timezone.utc)
            )
            session.add(obj)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise

def load_model_from_db_sync(station_code, model_name, session: Session):
    stmt = (
        select(MLModel)
        .where(
            MLModel.station_code == station_code,
            MLModel.model_name == model_name
        )
        .order_by(MLModel.trained_at.desc())
    )
    result = session.execute(stmt)
    obj = result.scalars().first()
    return obj.model if obj else None