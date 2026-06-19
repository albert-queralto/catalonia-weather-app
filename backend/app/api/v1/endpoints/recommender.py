import uuid
from zoneinfo import ZoneInfo
import pandas as pd
from sqlalchemy import text
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import datetime, timedelta, timezone

from app.services.recommender import fetch_weather_slice
from app.core.config import settings
from app.services.user.auth import get_current_user, require_role
from app.db.session import get_session
from app.db.models import User

from app.services.recommender.schemas import ActivityOut, EventIn
from app.services.recommender.utils import get_weather_for_event
from app.services.air_quality.service import air_quality_service
from app.services.alerts.service import alerts_service
from app.services.recommender.features import fetch_weather_timeline
from app.services.recommender.service import (
    AlertContext,
    MLRecommender,
    build_scoring_windows,
    recommend,
)

router = APIRouter(tags=["recommender"])

model = MLRecommender(settings.model_path)
model.load()


CATALONIA_TZ = ZoneInfo("Europe/Madrid")


def _hydrate_context_from_view(ev: EventIn, db: Session, user: User) -> Optional[dict]:
    if not ev.request_id:
        return None
    
    row = db.execute(
        text(
            """
            SELECT
                position,
                user_lat,
                user_lon,
                weather_temp_c,
                weather_precip_prob,
                weather_wind_kmh,
                weather_is_day
            FROM events
            WHERE user_id = :uid
                AND request_id = :rid
                AND activity_id = :aid
                AND event_type = 'view'
            ORDER BY ts DESC
            LIMIT 1
            """
        ),
        {
            "uid": str(user.id),
            "rid": str(ev.request_id),
            "aid": str(ev.activity_id),
        },
    ).fetchone()
    
    if row is None:
        return None
    
    return {
        "position": row[0],
        "user_lat": row[1],
        "user_lon": row[2],
        "weather_temp_c": row[3],
        "weather_precip_prob": row[4],
        "weather_wind_kmh": row[5],
        "weather_is_day": row[6],
    }


def _parse_meteocat_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=CATALONIA_TZ)

        return dt.astimezone(timezone.utc)

    except ValueError:
        return None


def _lookup_comarca_code(db: Session, lat: float, lon: float) -> Optional[int]:
    row = db.execute(
        text(
            """
            SELECT code
            FROM comarcas
            WHERE ST_Contains(geom, ST_SetSRID(ST_Point(:lon, :lat), 4326))
            LIMIT 1
            """
        ),
        {"lat": lat, "lon": lon},
    ).first()

    if not row:
        return None

    try:
        return int(str(row[0]))
    except ValueError:
        return None


async def _get_alert_context(
    db: Session,
    lat: float,
    lon: float,
    planning_hours: int,
) -> AlertContext:
    """
    Gets the strongest active Meteocat SMP warning for the selected comarca.
    Fails softly so recommendations still work if Meteocat is unavailable.
    """
    comarca_code = _lookup_comarca_code(db, lat, lon)

    if comarca_code is None:
        return AlertContext()

    now_local = datetime.now(CATALONIA_TZ)
    window_start = now_local.astimezone(timezone.utc)
    window_end = window_start + timedelta(hours=planning_hours)

    days = {
        now_local.date(),
        (now_local + timedelta(days=1)).date(),
        (now_local + timedelta(days=2)).date(),
    }

    max_severity = 0
    meteors: set[str] = set()

    try:
        for day in sorted(days):
            episodes = await alerts_service.get_episodis_oberts(
                day.year,
                day.month,
                day.day,
            )

            for episode in episodes:
                meteor_name = episode.meteor.nom if episode.meteor else "weather"

                for avis in episode.avisos:
                    avis_start = _parse_meteocat_dt(avis.dataInici) or window_start
                    avis_end = _parse_meteocat_dt(avis.dataFi) or window_end

                    if avis_end < window_start or avis_start > window_end:
                        continue

                    for evolucio in avis.evolucions:
                        for periode in evolucio.periodes:
                            for afectacio in periode.afectacions or []:
                                if afectacio.idComarca != comarca_code:
                                    continue

                                severity = max(
                                    int(afectacio.perill or 0),
                                    int(afectacio.nivell or 0),
                                )

                                if severity > 0:
                                    max_severity = max(max_severity, severity)
                                    meteors.add(meteor_name)

    except Exception:
        return AlertContext()

    return AlertContext(
        severity=max_severity,
        meteors=tuple(sorted(meteors)),
    )


@router.post("/events")
def log_event(
    ev: EventIn, 
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    # Fetch weather data for the event location and time
    event_time = ev.ts.isoformat() if ev.ts else pd.Timestamp.now(tz="UTC").isoformat()
    weather = get_weather_for_event(ev.user_lat, ev.user_lon, event_time)
    context = _hydrate_context_from_view(ev, db, user) or {}

    position = ev.position if ev.position is not None else context.get("position")
    user_lat = ev.user_lat if ev.user_lat is not None else context.get("user_lat")
    user_lon = ev.user_lon if ev.user_lon is not None else context.get("user_lon")

    weather_temp_c = ev.weather_temp_c if ev.weather_temp_c is not None else context.get("weather_temp_c")
    weather_precip_prob = ev.weather_precip_prob if ev.weather_precip_prob is not None else context.get("weather_precip_prob")
    weather_wind_kmh = ev.weather_wind_kmh if ev.weather_wind_kmh is not None else context.get("weather_wind_kmh")
    weather_is_day = ev.weather_is_day if ev.weather_is_day is not None else context.get("weather_is_day")

    # Absolute fallback for old clients that do not send the served weather snapshot
    if (
        user_lat is not None
        and user_lon is not None
        and (
            weather_temp_c is None
            or weather_precip_prob is None
            or weather_wind_kmh is None
            or weather_is_day is None
        )
    ):
        event_time = ev.ts.isoformat() if ev.ts else pd.Timestamp.now(tz="UTC").isoformat()
        weather = get_weather_for_event(user_lat, user_lon, event_time)
        weather_temp_c = weather_temp_c if weather_temp_c is not None else weather["weather_temp_c"]
        weather_precip_prob = weather_precip_prob if weather_precip_prob is not None else weather["weather_precip_prob"]
        weather_wind_kmh = weather_wind_kmh if weather_wind_kmh is not None else weather["weather_wind_kmh"]
        weather_is_day = weather_is_day if weather_is_day is not None else weather["weather_is_day"]

    db.execute(
        text("""
        INSERT INTO events (
          id, user_id, activity_id, event_type, ts,
          request_id, position,
          user_lat, user_lon,
          weather_temp_c, weather_precip_prob, weather_wind_kmh, weather_is_day,
          rating
        )
        VALUES (
          :id, :u, :a, :t, COALESCE(:ts, now()),
          :rid, :pos,
          :lat, :lon,
          :temp, :pp, :wind, :day,
          :rating
        )
        """),
        {
            "id": str(uuid.uuid4()),
            "u": str(user.id),
            "a": str(ev.activity_id),
            "t": ev.event_type,
            "ts": ev.ts,
            "rid": str(ev.request_id) if ev.request_id else None,
            "pos": position,
            "lat": user_lat,
            "lon": user_lon,
            "temp": weather_temp_c,
            "pp": weather_precip_prob,
            "wind": weather_wind_kmh,
            "day": weather_is_day,
            "rating": ev.rating,
        }
    )
    db.commit()
    return {"ok": True}

@router.get("/recommendations", response_model=list[ActivityOut])
async def get_recommendations(
    lat: float,
    lon: float,
    radius_km: float = 8.0,
    horizon_hours: int = Query(4, ge=1, le=12),
    planning_hours: int = Query(48, ge=24, le=72),
    limit: int = Query(20, ge=1, le=50),
    sensitive_to_air_quality: bool = False,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    request_id = uuid.uuid4()

    weather_points = await fetch_weather_timeline(
        lat,
        lon,
        planning_hours=planning_hours,
    )

    weather_windows = build_scoring_windows(
        weather_points,
        horizon_hours=horizon_hours,
        planning_hours=planning_hours,
    )

    try:
        air_quality_points = await air_quality_service.get_air_quality_hourly(lat, lon)
    except Exception:
        air_quality_points = []

    alert_context = await _get_alert_context(
        db,
        lat,
        lon,
        planning_hours,
    )

    recs = recommend(
        db=db,
        model=model,
        user_id=user.id,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        limit=limit,
        weather_windows=weather_windows,
        air_quality_points=air_quality_points,
        alert_context=alert_context,
        sensitive_to_air_quality=sensitive_to_air_quality,
    )

    for idx, r in enumerate(recs, start=1):
        db.execute(
            text(
                """
                INSERT INTO events (
                    id, user_id, activity_id, event_type, ts,
                    request_id, position,
                    user_lat, user_lon,
                    weather_temp_c, weather_precip_prob, weather_wind_kmh, weather_is_day, rating
                )
                VALUES (
                    :id, :u, :a, 'view', now(),
                    :rid, :pos,
                    :lat, :lon,
                    :t, :pp, :w, :day, NULL
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "u": str(user.id),
                "a": str(r["id"]),
                "rid": str(request_id),
                "pos": idx,
                "lat": float(lat),
                "lon": float(lon),
                "t": float(r.get("weather_temp_c") or 0.0),
                "pp": float(r.get("weather_precip_prob") or 0.0),
                "w": float(r.get("weather_wind_kmh") or 0.0),
                "day": float(r.get("weather_is_day") or 1.0),
            },
        )

    db.commit()

    for idx, r in enumerate(recs, start=1):
        r["request_id"] = str(request_id)
        r["position"] = idx

    return recs

@router.post("/model/reload")
def reload_model(admin: User = Depends(require_role("admin"))):
    model.load()
    return {"ok": True, "model_loaded": model.model is not None}