from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from app.db.models import MLModel
from datetime import datetime, timezone

async def save_model_to_db(station_code, model_name, model_bytes, session: AsyncSession):
    try:
        result = await session.execute(
            select(MLModel).where(
                MLModel.station_code == station_code,
                MLModel.model_name == model_name
            )
        )
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
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise

async def load_model_from_db(station_code, model_name, session: AsyncSession):
    result = await session.execute(
        select(MLModel)
        .where(
            MLModel.station_code == station_code,
            MLModel.model_name == model_name
        )
        .order_by(MLModel.trained_at.desc())
    )
    obj = result.scalars().first()
    return obj.model if obj else None