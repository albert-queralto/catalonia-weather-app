from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Optional

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import ForecastHourly, ForecastSnapshot, MeteocatStation
from app.services.station_analytics.schemas import (
    ForecastAccuracyPointOut,
    ForecastAccuracySummaryOut,
)


METRIC_TO_FORECAST_COLUMN = {
    "temperature": "temperature_c",
    "precipitation": "precipitation_mm",
    "wind": "wind_speed_kmh",
}


def _date_start(value: date) -> datetime:
    return datetime(value.year, value.month, value.day)


def _date_end_exclusive(value: date) -> datetime:
    return _date_start(value) + timedelta(days=1)


async def fetch_openmeteo_station_forecast(
    *,
    lat: float,
    lon: float,
    forecast_days: int = 7,
) -> list[dict]:
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation,precipitation_probability,wind_speed_10m",
        "timezone": "UTC",
        "forecast_days": forecast_days,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    hourly = data.get("hourly") or {}

    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    precipitation = hourly.get("precipitation") or []
    precipitation_probability = hourly.get("precipitation_probability") or []
    wind = hourly.get("wind_speed_10m") or []

    result = []

    for i, ts in enumerate(times):
        target_time = datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)

        result.append(
            {
                "target_time": target_time,
                "temperature_c": float(temps[i]) if temps[i] is not None else None,
                "precipitation_mm": float(precipitation[i]) if precipitation[i] is not None else None,
                "precipitation_probability": float(precipitation_probability[i]) if precipitation_probability[i] is not None else None,
                "wind_speed_kmh": float(wind[i]) if wind[i] is not None else None,
            }
        )

    return result


async def capture_openmeteo_forecast_for_station(
    db: Session,
    *,
    station: MeteocatStation,
) -> int:
    if station.latitud is None or station.longitud is None:
        return 0

    created_at = datetime.utcnow()

    hourly = await fetch_openmeteo_station_forecast(
        lat=station.latitud,
        lon=station.longitud,
        forecast_days=7,
    )

    snapshot = ForecastSnapshot(
        provider="open_meteo",
        station_code=station.codi,
        latitud=station.latitud,
        longitud=station.longitud,
        created_at=created_at,
    )

    db.add(snapshot)
    db.flush()

    for row in hourly:
        db.add(
            ForecastHourly(
                snapshot_id=snapshot.id,
                target_time=row["target_time"],
                temperature_c=row["temperature_c"],
                precipitation_mm=row["precipitation_mm"],
                precipitation_probability=row["precipitation_probability"],
                wind_speed_kmh=row["wind_speed_kmh"],
            )
        )

    db.commit()

    return len(hourly)


async def capture_openmeteo_forecasts_for_all_stations(db: Session, limit: Optional[int] = None) -> dict:
    query = db.query(MeteocatStation).filter(
        MeteocatStation.latitud.isnot(None),
        MeteocatStation.longitud.isnot(None),
    )

    if limit:
        query = query.limit(limit)

    stations = query.all()

    captured = 0
    rows = 0

    for station in stations:
        rows += await capture_openmeteo_forecast_for_station(db, station=station)
        captured += 1

    return {
        "stations": captured,
        "forecast_rows": rows,
    }


def fetch_observed_points(
    db: Session,
    *,
    station_code: str,
    variable_code: int,
    date_from: date,
    date_to: date,
) -> list[tuple[datetime, float]]:
    rows = db.execute(
        text(
            """
            SELECT
                date_trunc('hour', COALESCE(v.data, m.date)) AS time,
                AVG(v.valor) AS observed
            FROM station_measurements m
            JOIN station_variable_values v
                ON v.measurement_id = m.id
            WHERE m.codi_estacio = :station_code
              AND v.codi_variable = :variable_code
              AND COALESCE(v.data, m.date) >= :start_dt
              AND COALESCE(v.data, m.date) < :end_dt
            GROUP BY 1
            ORDER BY 1
            """
        ),
        {
            "station_code": station_code,
            "variable_code": variable_code,
            "start_dt": _date_start(date_from),
            "end_dt": _date_end_exclusive(date_to),
        },
    ).fetchall()

    return [(row.time, float(row.observed)) for row in rows]


def nearest_forecast_for_target(
    db: Session,
    *,
    station_code: str,
    target_time: datetime,
    metric: str,
    lead_hours: int,
    tolerance_hours: int = 6,
) -> Optional[float]:
    column = METRIC_TO_FORECAST_COLUMN[metric]

    desired_snapshot_time = target_time - timedelta(hours=lead_hours)

    row = db.execute(
        text(
            f"""
            SELECT
                fh.{column} AS forecast,
                ABS(EXTRACT(EPOCH FROM (fs.created_at - :desired_snapshot_time))) AS distance_seconds
            FROM forecast_snapshots fs
            JOIN forecast_hourly fh
                ON fh.snapshot_id = fs.id
            WHERE fs.station_code = :station_code
              AND fs.provider = 'open_meteo'
              AND fh.target_time = :target_time
              AND fh.{column} IS NOT NULL
              AND fs.created_at BETWEEN :min_snapshot_time AND :max_snapshot_time
            ORDER BY distance_seconds
            LIMIT 1
            """
        ),
        {
            "station_code": station_code,
            "target_time": target_time,
            "desired_snapshot_time": desired_snapshot_time,
            "min_snapshot_time": desired_snapshot_time - timedelta(hours=tolerance_hours),
            "max_snapshot_time": desired_snapshot_time + timedelta(hours=tolerance_hours),
        },
    ).first()

    if not row:
        return None

    return float(row.forecast)


def build_forecast_accuracy(
    db: Session,
    *,
    station_code: str,
    variable_code: int,
    metric: str,
    date_from: date,
    date_to: date,
    lead_hours: int = 24,
) -> ForecastAccuracySummaryOut:
    if metric not in METRIC_TO_FORECAST_COLUMN:
        raise ValueError("metric must be one of: temperature, precipitation, wind")

    observed = fetch_observed_points(
        db,
        station_code=station_code,
        variable_code=variable_code,
        date_from=date_from,
        date_to=date_to,
    )

    points: list[ForecastAccuracyPointOut] = []

    for target_time, observed_value in observed:
        forecast_value = nearest_forecast_for_target(
            db,
            station_code=station_code,
            target_time=target_time,
            metric=metric,
            lead_hours=lead_hours,
        )

        if forecast_value is None:
            continue

        error = forecast_value - observed_value

        points.append(
            ForecastAccuracyPointOut(
                time=target_time,
                observed=observed_value,
                forecast=forecast_value,
                error=error,
                absolute_error=abs(error),
            )
        )

    if not points:
        return ForecastAccuracySummaryOut(
            provider="open_meteo",
            station_code=station_code,
            metric=metric,
            lead_hours=lead_hours,
            sample_count=0,
            points=[],
        )

    mae = sum(p.absolute_error for p in points) / len(points)
    bias = sum(p.error for p in points) / len(points)
    rmse = math.sqrt(sum(p.error ** 2 for p in points) / len(points))

    return ForecastAccuracySummaryOut(
        provider="open_meteo",
        station_code=station_code,
        metric=metric,
        lead_hours=lead_hours,
        sample_count=len(points),
        mae=mae,
        rmse=rmse,
        bias=bias,
        points=points,
    )