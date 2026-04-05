import uuid
import pandas as pd
from sqlalchemy import text
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from app.services.recommender import MLRecommender, recommend, fetch_weather_slice
from app.core.config import settings
from app.services.user.auth import get_current_user, require_role
from app.db.session import get_session
from app.db.models import User
from app.services.recommender.schemas import ActivityOut, EventIn
from app.services.recommender.utils import get_weather_for_event

router = APIRouter(tags=["recommender"])

model = MLRecommender(settings.model_path)
model.load()


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
    horizon_hours: int = 4,
    limit: int = 20,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),  # requires login
):
    request_id = uuid.uuid4()

    w = await fetch_weather_slice(lat, lon, horizon_hours=horizon_hours)
    recs = recommend(
        db=db,
        model=model,
        user_id=user.id,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        weather_temp_c=w.temp_c,
        weather_precip_prob=w.precip_prob,
        weather_wind_kmh=w.wind_kmh,
        weather_is_day=w.is_day,
        limit=limit,
    )
    
    for idx, r in enumerate(recs, start=1):
        db.execute(
            text("""
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
            """),
            {
                "id": str(uuid.uuid4()),
                "u": str(user.id),
                "a": str(r["id"]),
                "rid": str(request_id),
                "pos": idx,
                "lat": float(lat),
                "lon": float(lon),
                "t": float(w.temp_c),
                "pp": float(w.precip_prob),
                "w": float(w.wind_kmh),
                "day": float(w.is_day),
                "rating": None,
            }
        )

    db.commit()
    
    # Include request_id in response so the client can attach it to clicks/saves
    for idx, r in enumerate(recs, start=1):
        r["request_id"] = str(request_id)
        r["position"] = idx
        r["weather_temp_c"] = float(w.temp_c)
        r["weather_precip_prob"] = float(w.precip_prob)
        r["weather_wind_kmh"] = float(w.wind_kmh)
        r["weather_is_day"] = float(w.is_day)
    
    return recs

@router.post("/model/reload")
def reload_model(admin: User = Depends(require_role("admin"))):
    model.load()
    return {"ok": True, "model_loaded": model.model is not None}