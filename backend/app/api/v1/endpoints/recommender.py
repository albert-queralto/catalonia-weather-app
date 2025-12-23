import uuid
from sqlalchemy import text
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.services.recommender import MLRecommender, recommend, fetch_weather_slice
from app.core.config import settings
from app.services.user.auth import get_current_user, require_role
from app.db.session import get_session
from app.db.models import User
from app.services.recommender.schemas import ActivityOut, EventIn

router = APIRouter(prefix="/recommender", tags=["recommender"])

model = MLRecommender(settings.model_path)
model.load()

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
            weather_temp_c, weather_precip_prob, weather_wind_kmh, weather_is_day
            )
            VALUES (
            :id, :u, :a, 'view', now(),
            :rid, :pos,
            :lat, :lon,
            :t, :pp, :w, :day
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
            }
        )

    db.commit()
    
    # Include request_id in response so the client can attach it to clicks/saves
    for r in recs:
        r["request_id"] = str(request_id)
    
    return recs

@router.post("/model/reload")
def reload_model(admin: User = Depends(require_role("admin"))):
    model.load()
    return {"ok": True, "model_loaded": model.model is not None}

@router.post("/events")
def log_event(ev: EventIn, db: Session = Depends(get_session)):
    db.execute(
        text("""
        INSERT INTO events (
          id, user_id, activity_id, event_type, ts,
          request_id, position,
          user_lat, user_lon,
          weather_temp_c, weather_precip_prob, weather_wind_kmh, weather_is_day
        )
        VALUES (
          :id, :u, :a, :t, COALESCE(:ts, now()),
          :rid, :pos,
          :lat, :lon,
          :temp, :pp, :wind, :day
        )
        """),
        {
            "id": str(uuid.uuid4()),
            "u": str(ev.user_id),
            "a": str(ev.activity_id),
            "t": ev.event_type,
            "ts": ev.ts,
            "rid": str(ev.request_id) if ev.request_id else None,
            "pos": ev.position,
            "lat": ev.user_lat,
            "lon": ev.user_lon,
            "temp": ev.weather_temp_c,
            "pp": ev.weather_precip_prob,
            "wind": ev.weather_wind_kmh,
            "day": ev.weather_is_day,
        }
    )
    db.commit()
    return {"ok": True}
