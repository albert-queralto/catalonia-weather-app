from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.services.ml import (
    activate_trained_model,
    available_model_names,
    delete_trained_model,
    get_trained_model,
    list_trained_models,
    train_and_save_model,
)
from app.services.user.auth import require_role

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


@router.get("/trained-models")
def list_station_models() -> dict[str, Any]:
    models = list_trained_models()
    active = [model for model in models if model.get("active")]
    return {
        "count": len(models),
        "active_count": len(active),
        "models": models,
    }


@router.get("/trained-models/{model_id}")
def get_station_model(model_id: str) -> dict[str, Any]:
    try:
        return get_trained_model(model_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/train")
def train_station_model(
    payload: TrainStationModelIn,
    db: Session = Depends(get_session),
    _admin: object = Depends(require_role("admin")),
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


@router.post("/trained-models/{model_id}/activate")
def activate_station_model(
    model_id: str,
    _admin: object = Depends(require_role("admin")),
) -> dict[str, Any]:
    try:
        return activate_trained_model(model_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/trained-models/{model_id}")
def delete_station_model(
    model_id: str,
    _admin: object = Depends(require_role("admin")),
) -> dict[str, Any]:
    try:
        return delete_trained_model(model_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
