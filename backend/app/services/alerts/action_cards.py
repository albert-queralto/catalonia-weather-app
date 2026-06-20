from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from typing import Iterable, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.alerts.schemas import (
    EpisodiObert,
    AlertActionCard,
    AlertComarcaOut,
    AffectedActivityOut,
    AlertTimelineSlot,
)

CATALONIA_TZ = ZoneInfo("Europe/Madrid")


def parse_meteocat_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CATALONIA_TZ)

    return dt.astimezone(CATALONIA_TZ)


def comarca_code_from_meteocat_id(value: Optional[int]) -> Optional[str]:
    if value is None:
        return None

    return str(value).zfill(2)


def severity_label(severity: int) -> str:
    if severity <= 0:
        return "No danger"
    if severity <= 2:
        return "Moderate"
    if severity <= 4:
        return "High"
    return "Very high"


def period_interval(
    *,
    base_day: str,
    period_name: str,
    fallback_start: datetime,
    fallback_end: datetime,
) -> tuple[datetime, datetime]:
    """
    Meteocat periods are often labels such as '00-06', '06-12', etc.
    This tries to convert the period name into local start/end datetimes.

    If the label cannot be parsed, it falls back to the aviso start/end.
    """
    numbers = [int(x) for x in re.findall(r"\d{1,2}", period_name or "")]

    if len(numbers) >= 2:
        start_hour, end_hour = numbers[0], numbers[1]

        try:
            day_dt = datetime.fromisoformat(base_day[:10]).date()
        except ValueError:
            day_dt = fallback_start.date()

        start_dt = datetime.combine(day_dt, time(start_hour, 0), tzinfo=CATALONIA_TZ)

        if end_hour == 24:
            end_dt = datetime.combine(day_dt + timedelta(days=1), time(0, 0), tzinfo=CATALONIA_TZ)
        else:
            end_dt = datetime.combine(day_dt, time(end_hour, 0), tzinfo=CATALONIA_TZ)

        if end_dt <= start_dt:
            end_dt += timedelta(days=1)

        return start_dt, end_dt

    return fallback_start, fallback_end


def recommended_action_for(meteor: str, severity: int) -> str:
    m = meteor.lower()

    if severity >= 5:
        return "Avoid non-essential outdoor activity and follow official emergency guidance."

    if "pluja" in m or "rain" in m or "precipit" in m:
        if severity >= 3:
            return "Avoid exposed outdoor plans. Prioritize indoor activities and check transport conditions."
        return "Carry rain protection and prefer covered or short outdoor activities."

    if "vent" in m or "wind" in m:
        if severity >= 3:
            return "Avoid exposed areas, mountains, forests, and activities affected by strong wind."
        return "Prefer sheltered routes and avoid activities sensitive to wind."

    if "neu" in m or "snow" in m:
        return "Avoid mountain travel unless prepared. Check road and access conditions."

    if "calor" in m or "heat" in m:
        return "Avoid intense outdoor activity during peak heat. Prefer shaded, indoor, or evening plans."

    if "fred" in m or "cold" in m:
        return "Dress warmly and prefer shorter or indoor activities."

    return "Check the alert details and adapt outdoor plans."


def recommender_effect_for(meteor: str, severity: int) -> str:
    if severity >= 4:
        return "Outdoor activities are hidden or heavily downranked; indoor alternatives are prioritized."

    if severity >= 2:
        return "Outdoor activities are downranked; covered and indoor alternatives are boosted."

    return "Warning badge shown on affected outdoor activities."


def load_comarca_names(db: Session) -> dict[str, str]:
    rows = db.execute(text("SELECT code, name FROM comarcas")).fetchall()
    return {str(row.code): row.name for row in rows}


def find_affected_activities(
    db: Session,
    *,
    comarca_codes: list[str],
    lat: Optional[float],
    lon: Optional[float],
    radius_km: float,
    severity: int,
    limit: int = 8,
) -> list[AffectedActivityOut]:
    """
    Returns nearby activities affected by this alert.

    For severity >= 2, only outdoor / uncovered activities are considered affected.
    """
    if not comarca_codes:
        return []

    params = {
        "codes": comarca_codes,
        "limit": limit,
    }

    distance_filter = ""

    if lat is not None and lon is not None:
        distance_filter = """
        AND ST_DWithin(
            a.location,
            ST_SetSRID(ST_Point(:lon, :lat), 4326)::geography,
            :radius_m
        )
        """
        params.update(
            {
                "lat": lat,
                "lon": lon,
                "radius_m": radius_km * 1000,
            }
        )

    outdoor_filter = ""

    if severity >= 2:
        outdoor_filter = "AND a.indoor = false"

    rows = db.execute(
        text(
            f"""
            SELECT
                a.id::text AS id,
                a.name,
                a.category,
                a.indoor
            FROM activities a
            JOIN comarcas c
                ON c.code = ANY(:codes)
                AND ST_Contains(c.geom, a.location::geometry)
            WHERE a.validated = true
            {distance_filter}
            {outdoor_filter}
            ORDER BY a.created_at DESC
            LIMIT :limit
            """
        ),
        params,
    ).fetchall()

    return [
        AffectedActivityOut(
            id=row.id,
            name=row.name,
            category=row.category,
            indoor=row.indoor,
        )
        for row in rows
    ]


def build_action_cards(
    *,
    db: Session,
    episodis: Iterable[EpisodiObert],
    subscribed_comarques: Optional[set[str]] = None,
    meteor_types: Optional[set[str]] = None,
    min_severity: int = 0,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: float = 8.0,
) -> list[AlertActionCard]:
    """
    Converts raw Meteocat nested episodes into user-facing alert cards.
    """
    comarca_names = load_comarca_names(db)
    cards: list[AlertActionCard] = []

    subscribed_comarques = subscribed_comarques or set()
    meteor_types = {m.lower() for m in meteor_types or set() if m}

    for episode in episodis:
        meteor = episode.meteor.nom if episode.meteor else "Weather"

        if meteor_types and meteor.lower() not in meteor_types:
            continue

        for aviso in episode.avisos or []:
            aviso_start = parse_meteocat_datetime(aviso.dataInici) or datetime.now(CATALONIA_TZ)
            aviso_end = parse_meteocat_datetime(aviso.dataFi) or aviso_start + timedelta(hours=6)

            for evolucio in aviso.evolucions or []:
                for periode in evolucio.periodes or []:
                    starts_at, ends_at = period_interval(
                        base_day=evolucio.dia,
                        period_name=periode.nom,
                        fallback_start=aviso_start,
                        fallback_end=aviso_end,
                    )

                    affected_by_code: dict[str, AlertComarcaOut] = {}

                    for afectacio in periode.afectacions or []:
                        code = comarca_code_from_meteocat_id(afectacio.idComarca)

                        if not code:
                            continue

                        severity = max(int(afectacio.perill or 0), int(afectacio.nivell or 0))

                        if severity < min_severity:
                            continue

                        if subscribed_comarques and code not in subscribed_comarques:
                            continue

                        existing = affected_by_code.get(code)

                        if existing is None or severity > existing.severity:
                            affected_by_code[code] = AlertComarcaOut(
                                code=code,
                                name=comarca_names.get(code, code),
                                severity=severity,
                                threshold=afectacio.llindar,
                            )

                    if not affected_by_code:
                        continue

                    max_severity = max(c.severity for c in affected_by_code.values())
                    affected_codes = list(affected_by_code.keys())

                    affected_activities = find_affected_activities(
                        db,
                        comarca_codes=affected_codes,
                        lat=lat,
                        lon=lon,
                        radius_km=radius_km,
                        severity=max_severity,
                    )

                    cards.append(
                        AlertActionCard(
                            id=str(uuid.uuid4()),
                            meteor=meteor,
                            severity=max_severity,
                            severity_label=severity_label(max_severity),
                            starts_at=starts_at,
                            ends_at=ends_at,
                            affected_comarques=sorted(
                                affected_by_code.values(),
                                key=lambda c: c.name,
                            ),
                            recommended_action=recommended_action_for(meteor, max_severity),
                            recommender_effect=recommender_effect_for(meteor, max_severity),
                            affected_recommended_activities=affected_activities,
                        )
                    )

    cards.sort(key=lambda c: (c.starts_at, -c.severity, c.meteor))

    return cards


def build_timeline(
    *,
    cards: list[AlertActionCard],
    days: int = 2,
) -> list[AlertTimelineSlot]:
    """
    Builds 6-hour timeline blocks:
    00–06, 06–12, 12–18, 18–24.
    """
    now = datetime.now(CATALONIA_TZ)
    current_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

    slots: list[AlertTimelineSlot] = []

    for day_offset in range(days):
        day_start = current_day + timedelta(days=day_offset)

        for start_hour in (0, 6, 12, 18):
            slot_start = day_start + timedelta(hours=start_hour)
            slot_end = slot_start + timedelta(hours=6)

            slot_cards = [
                card
                for card in cards
                if card.starts_at < slot_end and card.ends_at > slot_start
            ]

            max_sev = max((card.severity for card in slot_cards), default=0)

            label = f"{slot_start.strftime('%a %d/%m')} {slot_start.strftime('%H:%M')}–{slot_end.strftime('%H:%M')}"

            slots.append(
                AlertTimelineSlot(
                    label=label,
                    starts_at=slot_start,
                    ends_at=slot_end,
                    max_severity=max_sev,
                    cards=slot_cards,
                )
            )

    return slots