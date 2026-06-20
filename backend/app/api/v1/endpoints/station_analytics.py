from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.services.station_analytics.schemas import StationExplorerOut
from app.services.station_analytics.service import build_station_explorer
from app.db.models import MeteocatStation
from app.services.station_analytics.schemas import ForecastAccuracySummaryOut
from app.services.station_analytics.forecast_accuracy import (
    build_forecast_accuracy,
    capture_openmeteo_forecast_for_station,
    capture_openmeteo_forecasts_for_all_stations,
)

router = APIRouter()


@router.get("/stations/explorer", response_model=StationExplorerOut)
def get_station_explorer(
    station_code: str = Query(...),
    variable_code: int = Query(...),
    date_from: date = Query(...),
    date_to: date = Query(...),
    nearby_radius_km: float = Query(50, ge=1, le=200),
    reference_station_code: Optional[str] = Query(None),
    db: Session = Depends(get_session),
):
    if date_to < date_from:
        raise HTTPException(status_code=400, detail="date_to must be >= date_from")

    if date_to - date_from > timedelta(days=366):
        raise HTTPException(status_code=400, detail="Maximum range is 366 days")

    try:
        return build_station_explorer(
            db,
            station_code=station_code,
            variable_code=variable_code,
            date_from=date_from,
            date_to=date_to,
            nearby_radius_km=nearby_radius_km,
            reference_station_code=reference_station_code,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    
    
@router.post("/stations/{station_code}/forecast-snapshot")
async def capture_station_forecast_snapshot(
    station_code: str,
    db: Session = Depends(get_session),
):
    station = db.query(MeteocatStation).filter(MeteocatStation.codi == station_code).first()

    if not station:
        raise HTTPException(status_code=404, detail="Station not found")

    rows = await capture_openmeteo_forecast_for_station(db, station=station)

    return {
        "status": "ok",
        "station_code": station_code,
        "forecast_rows": rows,
    }


@router.post("/stations/forecast-snapshots/capture")
async def capture_all_station_forecast_snapshots(
    limit: Optional[int] = Query(None, ge=1, le=500),
    db: Session = Depends(get_session),
):
    return await capture_openmeteo_forecasts_for_all_stations(db, limit=limit)


@router.get("/stations/forecast-accuracy", response_model=ForecastAccuracySummaryOut)
def get_station_forecast_accuracy(
    station_code: str = Query(...),
    variable_code: int = Query(...),
    metric: str = Query(..., pattern="^(temperature|precipitation|wind)$"),
    date_from: date = Query(...),
    date_to: date = Query(...),
    lead_hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_session),
):
    if date_to < date_from:
        raise HTTPException(status_code=400, detail="date_to must be >= date_from")

    try:
        return build_forecast_accuracy(
            db,
            station_code=station_code,
            variable_code=variable_code,
            metric=metric,
            date_from=date_from,
            date_to=date_to,
            lead_hours=lead_hours,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))