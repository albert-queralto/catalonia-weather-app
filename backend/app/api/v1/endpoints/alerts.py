from datetime import datetime, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_session
from app.db.models import User
from app.services.user.auth import get_current_user
from app.services.alerts.service import alerts_service
from app.services.alerts.schemas import (
    EpisodiObert,
    AlertActionCard,
    AlertTimelineSlot,
)
from app.services.alerts.action_cards import build_action_cards, build_timeline

router = APIRouter()
CATALONIA_TZ = ZoneInfo("Europe/Madrid")


@router.get("/meteocat/episodis-oberts", response_model=List[EpisodiObert])
async def get_episodis_oberts(
    year: int = Query(..., ge=2000, le=2100, description="Year in YYYY format"),
    month: int = Query(..., ge=1, le=12, description="Month in MM format"),
    day: int = Query(..., ge=1, le=31, description="Day in DD format"),
):
    return await alerts_service.get_episodis_oberts(year, month, day)


def _lookup_comarca_code(db: Session, lat: float, lon: float) -> Optional[str]:
    row = db.execute(
        text(
            """
            SELECT code
            FROM comarcas
            WHERE ST_Contains(
                geom,
                ST_SetSRID(ST_Point(:lon, :lat), 4326)
            )
            LIMIT 1
            """
        ),
        {"lat": lat, "lon": lon},
    ).first()

    if not row:
        return None

    return str(row.code)


async def _load_episodes_for_next_days(days: int) -> list[EpisodiObert]:
    now = datetime.now(CATALONIA_TZ)
    all_episodes: list[EpisodiObert] = []

    for offset in range(days):
        day = now + timedelta(days=offset)

        try:
            episodes = await alerts_service.get_episodis_oberts(
                day.year,
                day.month,
                day.day,
            )
            all_episodes.extend(episodes)
        except Exception:
            # Fail softly. The UI should still load.
            continue

    return all_episodes


def _subscribed_comarques_for_user(
    db: Session,
    user: User,
    lat: Optional[float],
    lon: Optional[float],
) -> set[str]:
    codes = {str(c).zfill(2) for c in (user.favorite_comarques or []) if c}

    if user.alert_subscribe_current_location:
        if user.alert_current_comarca:
            codes.add(str(user.alert_current_comarca).zfill(2))
        elif lat is not None and lon is not None:
            current_code = _lookup_comarca_code(db, lat, lon)
            if current_code:
                codes.add(str(current_code).zfill(2))

    return codes


@router.get("/alerts/action-cards", response_model=list[AlertActionCard])
async def get_alert_action_cards(
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: float = Query(8.0, ge=0.5, le=100),
    days: int = Query(2, ge=1, le=3),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """
    Personalized alert cards based on:
    - favorite comarques
    - current location comarca
    - meteor type preferences
    - minimum severity
    """
    episodes = await _load_episodes_for_next_days(days)

    subscribed_comarques = _subscribed_comarques_for_user(db, user, lat, lon)

    # If the user has no subscribed comarca yet, use the current lat/lon comarca.
    if not subscribed_comarques and lat is not None and lon is not None:
        current_code = _lookup_comarca_code(db, lat, lon)
        if current_code:
            subscribed_comarques.add(str(current_code).zfill(2))

    return build_action_cards(
        db=db,
        episodis=episodes,
        subscribed_comarques=subscribed_comarques,
        meteor_types=set(user.alert_meteor_types or []),
        min_severity=int(user.alert_min_severity or 0),
        lat=lat,
        lon=lon,
        radius_km=radius_km,
    )


@router.get("/alerts/timeline", response_model=list[AlertTimelineSlot])
async def get_alert_timeline(
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: float = Query(8.0, ge=0.5, le=100),
    days: int = Query(2, ge=1, le=3),
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    cards = await get_alert_action_cards(
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        days=days,
        db=db,
        user=user,
    )

    return build_timeline(cards=cards, days=days)