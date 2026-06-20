from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import MeteocatStation, StationVariable
from app.services.station_analytics.schemas import (
    DailyStationStatOut,
    MissingIntervalOut,
    NearbyStationComparisonOut,
    SameDayLastYearOut,
    StationExplorerOut,
    StationSummaryOut,
    StationValuePointOut,
    StationVariableSummaryOut,
    WeekHistoricalAverageOut,
    MicroclimateInsightOut,
)


def _station_comarca_name(station: MeteocatStation) -> Optional[str]:
    if isinstance(station.comarca, dict):
        return station.comarca.get("nom")
    return None


def _date_start(value: date) -> datetime:
    return datetime(value.year, value.month, value.day)


def _date_end_exclusive(value: date) -> datetime:
    return _date_start(value) + timedelta(days=1)


def get_station_or_404_like(db: Session, station_code: str) -> MeteocatStation:
    station = db.query(MeteocatStation).filter(MeteocatStation.codi == station_code).first()

    if not station:
        raise ValueError(f"Station not found: {station_code}")

    return station


def get_variable_or_404_like(db: Session, variable_code: int) -> StationVariable:
    variable = db.query(StationVariable).filter(StationVariable.codi == variable_code).first()

    if not variable:
        raise ValueError(f"Variable not found: {variable_code}")

    return variable


def fetch_station_points(
    db: Session,
    *,
    station_code: str,
    variable_code: int,
    date_from: date,
    date_to: date,
) -> list[StationValuePointOut]:
    rows = db.execute(
        text(
            """
            SELECT
                COALESCE(v.data, m.date) AS time,
                v.valor AS value
            FROM station_measurements m
            JOIN station_variable_values v
                ON v.measurement_id = m.id
            WHERE m.codi_estacio = :station_code
              AND v.codi_variable = :variable_code
              AND COALESCE(v.data, m.date) >= :start_dt
              AND COALESCE(v.data, m.date) < :end_dt
            ORDER BY time
            """
        ),
        {
            "station_code": station_code,
            "variable_code": variable_code,
            "start_dt": _date_start(date_from),
            "end_dt": _date_end_exclusive(date_to),
        },
    ).fetchall()

    return [
        StationValuePointOut(
            time=row.time,
            value=float(row.value),
        )
        for row in rows
    ]


def infer_expected_daily_count(points: list[StationValuePointOut]) -> int:
    """
    Guesses how many values should exist per day.
    If hourly data: 24.
    If 30-minute data: 48.
    If daily data: 1.
    """
    if len(points) < 3:
        return 24

    sorted_points = sorted(points, key=lambda p: p.time)
    gaps_minutes: list[float] = []

    for prev, curr in zip(sorted_points, sorted_points[1:]):
        gap = (curr.time - prev.time).total_seconds() / 60

        if 0 < gap <= 24 * 60:
            gaps_minutes.append(gap)

    if not gaps_minutes:
        return 24

    gaps_minutes.sort()
    median_gap = gaps_minutes[len(gaps_minutes) // 2]

    if median_gap <= 0:
        return 24

    return max(1, round((24 * 60) / median_gap))


def build_daily_stats(
    points: list[StationValuePointOut],
    *,
    date_from: date,
    date_to: date,
    expected_daily_count: Optional[int] = None,
) -> list[DailyStationStatOut]:
    expected = expected_daily_count or infer_expected_daily_count(points)
    by_day: dict[date, list[float]] = defaultdict(list)

    for p in points:
        by_day[p.time.date()].append(p.value)

    result: list[DailyStationStatOut] = []

    current = date_from

    while current <= date_to:
        values = by_day.get(current, [])
        count = len(values)
        missing_count = max(0, expected - count)

        result.append(
            DailyStationStatOut(
                date=current,
                min_value=min(values) if values else None,
                max_value=max(values) if values else None,
                avg_value=sum(values) / count if values else None,
                count=count,
                expected_count=expected,
                missing_count=missing_count,
                missing_pct=round((missing_count / expected) * 100, 1) if expected else 0.0,
            )
        )

        current += timedelta(days=1)

    return result


def detect_missing_intervals(
    points: list[StationValuePointOut],
    *,
    expected_daily_count: Optional[int] = None,
) -> list[MissingIntervalOut]:
    if len(points) < 2:
        return []

    expected = expected_daily_count or infer_expected_daily_count(points)
    expected_step_hours = 24 / max(1, expected)

    sorted_points = sorted(points, key=lambda p: p.time)

    intervals: list[MissingIntervalOut] = []

    for prev, curr in zip(sorted_points, sorted_points[1:]):
        gap_hours = (curr.time - prev.time).total_seconds() / 3600

        if gap_hours > expected_step_hours * 1.5:
            intervals.append(
                MissingIntervalOut(
                    starts_at=prev.time,
                    ends_at=curr.time,
                    gap_hours=round(gap_hours, 2),
                )
            )

    return intervals


def average_for_range(
    db: Session,
    *,
    station_code: str,
    variable_code: int,
    start_dt: datetime,
    end_dt: datetime,
) -> Optional[float]:
    row = db.execute(
        text(
            """
            SELECT AVG(v.valor) AS avg_value
            FROM station_measurements m
            JOIN station_variable_values v
                ON v.measurement_id = m.id
            WHERE m.codi_estacio = :station_code
              AND v.codi_variable = :variable_code
              AND COALESCE(v.data, m.date) >= :start_dt
              AND COALESCE(v.data, m.date) < :end_dt
            """
        ),
        {
            "station_code": station_code,
            "variable_code": variable_code,
            "start_dt": start_dt,
            "end_dt": end_dt,
        },
    ).first()

    return float(row.avg_value) if row and row.avg_value is not None else None


def build_today_vs_last_year(
    db: Session,
    *,
    station_code: str,
    variable_code: int,
    reference_day: date,
) -> SameDayLastYearOut:
    current_start = _date_start(reference_day)
    current_end = _date_end_exclusive(reference_day)

    last_year_day = date(reference_day.year - 1, reference_day.month, reference_day.day)
    last_year_start = _date_start(last_year_day)
    last_year_end = _date_end_exclusive(last_year_day)

    current_avg = average_for_range(
        db,
        station_code=station_code,
        variable_code=variable_code,
        start_dt=current_start,
        end_dt=current_end,
    )

    last_year_avg = average_for_range(
        db,
        station_code=station_code,
        variable_code=variable_code,
        start_dt=last_year_start,
        end_dt=last_year_end,
    )

    delta = None

    if current_avg is not None and last_year_avg is not None:
        delta = current_avg - last_year_avg

    return SameDayLastYearOut(
        current_date=reference_day,
        current_avg=current_avg,
        last_year_date=last_year_day,
        last_year_avg=last_year_avg,
        delta=delta,
    )


def build_week_vs_historical_average(
    db: Session,
    *,
    station_code: str,
    variable_code: int,
    reference_day: date,
    years_back: int = 5,
) -> WeekHistoricalAverageOut:
    week_start = reference_day - timedelta(days=reference_day.weekday())
    week_end = week_start + timedelta(days=6)

    current_avg = average_for_range(
        db,
        station_code=station_code,
        variable_code=variable_code,
        start_dt=_date_start(week_start),
        end_dt=_date_end_exclusive(week_end),
    )

    historical_values: list[float] = []

    for years_ago in range(1, years_back + 1):
        try:
            historical_start = date(week_start.year - years_ago, week_start.month, week_start.day)
            historical_end = historical_start + timedelta(days=6)
        except ValueError:
            continue

        avg = average_for_range(
            db,
            station_code=station_code,
            variable_code=variable_code,
            start_dt=_date_start(historical_start),
            end_dt=_date_end_exclusive(historical_end),
        )

        if avg is not None:
            historical_values.append(avg)

    historical_avg = (
        sum(historical_values) / len(historical_values)
        if historical_values
        else None
    )

    delta = None

    if current_avg is not None and historical_avg is not None:
        delta = current_avg - historical_avg

    return WeekHistoricalAverageOut(
        current_week_start=week_start,
        current_week_end=week_end,
        current_avg=current_avg,
        historical_avg=historical_avg,
        delta=delta,
        years_used=len(historical_values),
    )


def nearby_station_comparison(
    db: Session,
    *,
    station: MeteocatStation,
    variable_code: int,
    date_from: date,
    date_to: date,
    radius_km: float = 50,
    limit: int = 5,
) -> list[NearbyStationComparisonOut]:
    if station.latitud is None or station.longitud is None:
        return []

    selected_avg = average_for_range(
        db,
        station_code=station.codi,
        variable_code=variable_code,
        start_dt=_date_start(date_from),
        end_dt=_date_end_exclusive(date_to),
    )

    rows = db.execute(
        text(
            """
            SELECT
                s.codi,
                s.nom,
                ST_Distance(
                    ST_SetSRID(ST_Point(s.longitud, s.latitud), 4326)::geography,
                    ST_SetSRID(ST_Point(:lon, :lat), 4326)::geography
                ) / 1000.0 AS distance_km
            FROM meteocat_stations s
            WHERE s.codi <> :station_code
              AND s.latitud IS NOT NULL
              AND s.longitud IS NOT NULL
              AND ST_DWithin(
                    ST_SetSRID(ST_Point(s.longitud, s.latitud), 4326)::geography,
                    ST_SetSRID(ST_Point(:lon, :lat), 4326)::geography,
                    :radius_m
              )
            ORDER BY distance_km
            LIMIT :limit
            """
        ),
        {
            "station_code": station.codi,
            "lat": station.latitud,
            "lon": station.longitud,
            "radius_m": radius_km * 1000,
            "limit": limit,
        },
    ).fetchall()

    result: list[NearbyStationComparisonOut] = []

    for row in rows:
        avg_value = average_for_range(
            db,
            station_code=row.codi,
            variable_code=variable_code,
            start_dt=_date_start(date_from),
            end_dt=_date_end_exclusive(date_to),
        )

        delta = None

        if selected_avg is not None and avg_value is not None:
            delta = avg_value - selected_avg

        result.append(
            NearbyStationComparisonOut(
                codi=row.codi,
                nom=row.nom,
                distance_km=round(float(row.distance_km), 2),
                avg_value=avg_value,
                delta_vs_selected=delta,
            )
        )

    return result


def _daypart(dt: datetime) -> str:
    h = dt.hour

    if 5 <= h < 12:
        return "morning"
    if 12 <= h < 18:
        return "afternoon"
    if 18 <= h < 23:
        return "evening"

    return "night"


def microclimate_insights(
    db: Session,
    *,
    station_code: str,
    reference_station_code: str,
    variable_code: int,
    date_from: date,
    date_to: date,
    unit: str,
) -> list[MicroclimateInsightOut]:
    selected_points = fetch_station_points(
        db,
        station_code=station_code,
        variable_code=variable_code,
        date_from=date_from,
        date_to=date_to,
    )

    reference_points = fetch_station_points(
        db,
        station_code=reference_station_code,
        variable_code=variable_code,
        date_from=date_from,
        date_to=date_to,
    )

    reference_station = get_station_or_404_like(db, reference_station_code)

    selected_by_hour = {
        p.time.replace(minute=0, second=0, microsecond=0): p.value
        for p in selected_points
    }

    reference_by_hour = {
        p.time.replace(minute=0, second=0, microsecond=0): p.value
        for p in reference_points
    }

    deltas_by_daypart: dict[str, list[float]] = defaultdict(list)

    for ts, selected_value in selected_by_hour.items():
        ref_value = reference_by_hour.get(ts)

        if ref_value is None:
            continue

        deltas_by_daypart[_daypart(ts)].append(selected_value - ref_value)

    insights: list[MicroclimateInsightOut] = []

    for daypart in ["morning", "afternoon", "evening", "night"]:
        values = deltas_by_daypart.get(daypart, [])

        if not values:
            insights.append(
                MicroclimateInsightOut(
                    reference_station_code=reference_station_code,
                    reference_station_name=reference_station.nom or reference_station_code,
                    daypart=daypart,
                    avg_delta=None,
                    sample_count=0,
                    text=f"Not enough data to compare this station with {reference_station.nom or reference_station_code} in the {daypart}.",
                )
            )
            continue

        avg_delta = sum(values) / len(values)

        if abs(avg_delta) < 0.5:
            text = f"This station is usually similar to {reference_station.nom} in the {daypart}."
        elif avg_delta < 0:
            text = f"This station is usually {abs(avg_delta):.1f}{unit} cooler than {reference_station.nom} in the {daypart}."
        else:
            text = f"This station is usually {avg_delta:.1f}{unit} warmer than {reference_station.nom} in the {daypart}."

        insights.append(
            MicroclimateInsightOut(
                reference_station_code=reference_station_code,
                reference_station_name=reference_station.nom or reference_station_code,
                daypart=daypart,
                avg_delta=avg_delta,
                sample_count=len(values),
                text=text,
            )
        )

    return insights


def build_station_explorer(
    db: Session,
    *,
    station_code: str,
    variable_code: int,
    date_from: date,
    date_to: date,
    nearby_radius_km: float = 50,
    reference_station_code: Optional[str] = None,
) -> StationExplorerOut:
    station = get_station_or_404_like(db, station_code)
    variable = get_variable_or_404_like(db, variable_code)

    points = fetch_station_points(
        db,
        station_code=station_code,
        variable_code=variable_code,
        date_from=date_from,
        date_to=date_to,
    )

    expected_count = infer_expected_daily_count(points)

    daily_stats = build_daily_stats(
        points,
        date_from=date_from,
        date_to=date_to,
        expected_daily_count=expected_count,
    )

    missing_intervals = detect_missing_intervals(
        points,
        expected_daily_count=expected_count,
    )

    nearby = nearby_station_comparison(
        db,
        station=station,
        variable_code=variable_code,
        date_from=date_from,
        date_to=date_to,
        radius_km=nearby_radius_km,
    )

    today_vs_last_year = build_today_vs_last_year(
        db,
        station_code=station_code,
        variable_code=variable_code,
        reference_day=date_to,
    )

    week_vs_history = build_week_vs_historical_average(
        db,
        station_code=station_code,
        variable_code=variable_code,
        reference_day=date_to,
    )

    microclimate = []

    if reference_station_code and reference_station_code != station_code:
        microclimate = microclimate_insights(
            db,
            station_code=station_code,
            reference_station_code=reference_station_code,
            variable_code=variable_code,
            date_from=date_from,
            date_to=date_to,
            unit=variable.unitat,
        )

    return StationExplorerOut(
        station=StationSummaryOut(
            codi=station.codi,
            nom=station.nom,
            latitud=station.latitud,
            longitud=station.longitud,
            altitud=station.altitud,
            comarca=_station_comarca_name(station),
        ),
        variable=StationVariableSummaryOut(
            codi=variable.codi,
            nom=variable.nom,
            unitat=variable.unitat,
            acronim=variable.acronim,
            tipus=variable.tipus,
            decimals=variable.decimals,
        ),
        points=points,
        daily_stats=daily_stats,
        missing_intervals=missing_intervals,
        nearby_comparison=nearby,
        today_vs_same_day_last_year=today_vs_last_year,
        this_week_vs_historical_average=week_vs_history,
        microclimate_insights=microclimate,
    )