from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.services.ml import available_model_names, train_and_save_model

router = APIRouter(prefix="/ml", tags=["ml"])


class TrainStationModelIn(BaseModel):
    station_code: str = Field(..., min_length=1)
    date_from: date
    date_to: date
    target_variable: str = "Precipitation"
    model_name: str = "xgboost"


@router.get("/models")
def list_ml_models() -> dict[str, list[str]]:
    return {"models": available_model_names()}


@router.post("/train")
def train_station_model(
    payload: TrainStationModelIn,
    db: Session = Depends(get_session),
) -> dict[str, Any]:
    try:
        return train_and_save_model(
            payload.station_code,
            payload.date_from,
            payload.date_to,
            payload.target_variable,
            payload.model_name,
            db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
