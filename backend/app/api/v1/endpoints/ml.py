from __future__ import annotations

from datetime import date, datetime, timezone
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
from app.workers.celery_app import celery_app
from app.workers.tasks import train_station_models as train_station_models_task

router = APIRouter(prefix="/ml", tags=["ml"])


class TrainStationModelIn(BaseModel):
    station_code: str = Field(..., min_length=1)
    date_from: date
    date_to: date
    target_variable: str = "Precipitation"
    model_name: str = "xgboost"


class TrainStationModelsTaskIn(BaseModel):
    station_codes: list[str] | None = None
    station_limit: int | None = Field(default=None, gt=0)
    date_from: date | None = None
    date_to: date | None = None
    target_variable: str = Field(default="Precipitation", min_length=1)
    model_name: str = Field(default="xgboost", min_length=1)


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


@router.post("/train/stations/task", status_code=202)
def enqueue_station_model_training(
    payload: TrainStationModelsTaskIn,
    _admin: object = Depends(require_role("admin")),
) -> dict[str, Any]:
    kwargs = payload.model_dump()
    kwargs["date_from"] = payload.date_from.isoformat() if payload.date_from else None
    kwargs["date_to"] = payload.date_to.isoformat() if payload.date_to else None

    try:
        task = train_station_models_task.apply_async(kwargs=kwargs)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not enqueue station model training task: {exc}",
        ) from exc

    return {
        "status": "queued",
        "task_id": task.id,
        "task_name": "app.workers.tasks.train_station_models",
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "parameters": kwargs,
    }


@router.get("/tasks/{task_id}")
def get_ml_task_status(
    task_id: str,
    _admin: object = Depends(require_role("admin")),
) -> dict[str, Any]:
    result = celery_app.AsyncResult(task_id)
    response: dict[str, Any] = {
        "task_id": task_id,
        "state": result.state,
    }

    if result.state == "PROGRESS" and isinstance(result.info, dict):
        response["progress"] = result.info
    elif result.successful():
        response["result"] = result.result
    elif result.failed():
        response["error"] = str(result.result)

    return response


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
