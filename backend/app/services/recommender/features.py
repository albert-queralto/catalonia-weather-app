from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime, timedelta, timezone

import httpx

@dataclass(frozen=True)
class ActivityRow:
    """
    Lightweight activity representation used by the recommender.
    This is typically built from SQL query rows (id/name/category/tags/etc + lat/lon).
    """
    id: str
    name: str
    category: str
    tags: List[str]
    indoor: bool
    covered: bool
    price_level: int
    difficulty: int
    duration_minutes: int
    lat: float
    lon: float


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in kilometers between two lat/lon points."""
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat / 2.0) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2.0) ** 2
    c = 2.0 * atan2(sqrt(a), sqrt(1.0 - a))
    return R * c


def build_features(
    user_pref: Dict[str, float],
    user_tag_pref: Dict[str, float],
    activity: ActivityRow,
    user_lat: float,
    user_lon: float,
    weather_temp_c: float,
    weather_precip_prob: float,
    weather_wind_kmh: float,
    weather_is_day: float,
) -> Dict[str, float]:
    """
    Build a consistent feature dictionary for ML scoring and heuristic fallback.

    Keep these feature names stable and aligned with:
      - ML training script feature_order
      - MLRecommender.score() input

    Notes:
      - weather_precip_prob is expected in [0..100]
      - weather_is_day is expected 0/1 (or fraction if averaged)
    """
    distance = haversine_km(user_lat, user_lon, activity.lat, activity.lon)

    cat_weight = float(user_pref.get(activity.category, 0.0))

    tag_overlap = 0.0
    tag_weighted = 0.0
    for t in activity.tags:
        w = user_tag_pref.get(t)
        if w is not None:
            tag_overlap += 1.0
            tag_weighted += float(w)

    indoor_f = 1.0 if activity.indoor else 0.0
    covered_f = 1.0 if activity.covered else 0.0

    # Weather penalties mostly matter for outdoor activities
    outdoor = 1.0 - indoor_f

    precip_penalty = outdoor * (float(weather_precip_prob) / 100.0)  # 0..1
    wind_penalty = outdoor * (float(weather_wind_kmh) / 50.0)        # rough scaling
    cold_penalty = outdoor * max(0.0, (10.0 - float(weather_temp_c)) / 10.0)
    heat_penalty = outdoor * max(0.0, (float(weather_temp_c) - 30.0) / 10.0)

    return {
        # core
        "distance_km": float(distance),
        "cat_weight": float(cat_weight),
        "tag_overlap": float(tag_overlap),
        "tag_weighted": float(tag_weighted),

        # item attributes
        "indoor": indoor_f,
        "covered": covered_f,
        "price_level": float(activity.price_level),
        "difficulty": float(activity.difficulty),
        "duration_minutes": float(activity.duration_minutes),

        # weather snapshot
        "temp_c": float(weather_temp_c),
        "precip_prob": float(weather_precip_prob),
        "wind_kmh": float(weather_wind_kmh),
        "is_day": float(weather_is_day),

        # derived weather sensitivity
        "precip_penalty": float(precip_penalty),
        "wind_penalty": float(wind_penalty),
        "cold_penalty": float(cold_penalty),
        "heat_penalty": float(heat_penalty),

        "position": 0.0,
    }


def reason_text(activity: ActivityRow, weather_precip_prob: float, weather_temp_c: float) -> str:
    """
    Simple explanation string for UI.
    """
    pp = float(weather_precip_prob)
    t = float(weather_temp_c)

    if activity.indoor and pp >= 40.0:
        return "Higher rain probability; indoor option prioritized."
    if activity.covered and pp >= 40.0:
        return "Rain likely; covered option reduces weather risk."
    if (not activity.indoor) and pp < 25.0 and 12.0 <= t <= 28.0:
        return "Favorable conditions for outdoor activities."
    if (not activity.indoor) and t < 8.0:
        return "Cold conditions; consider dressing warm or choosing indoor options."
    if (not activity.indoor) and t > 32.0:
        return "High temperatures; consider shorter outdoor activities or indoor options."
    return "Matched to your preferences and nearby."


@dataclass(frozen=True)
class WeatherSlice:
    """
    Aggregated weather snapshot over a time window.
    - precip_prob is in [0..100]
    - is_day is 0/1 (or average if mixed)
    """
    temp_c: float
    precip_prob: float
    wind_kmh: float
    is_day: float


def _parse_iso_utc(ts: str) -> datetime:
    # Open-Meteo returns ISO timestamps, usually without timezone; we use UTC.
    # Example: "2025-12-23T14:00"
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def fetch_weather_slice(
    lat: float,
    lon: float,
    horizon_hours: int = 4,
    start: Optional[datetime] = None,
) -> WeatherSlice:
    """
    Fetch hourly forecast from Open-Meteo and aggregate over [start, start+horizon_hours).

    Open-Meteo endpoint (no key):
      https://api.open-meteo.com/v1/forecast

    Returns:
      WeatherSlice(temp_c, precip_prob, wind_kmh, is_day)

    Notes:
    - Uses hourly: temperature_2m, precipitation_probability, windspeed_10m, is_day
    - Uses timezone=UTC to simplify server-side handling.
    """
    if horizon_hours <= 0:
        raise ValueError("horizon_hours must be > 0")

    if start is None:
        start = datetime.now(timezone.utc)
    else:
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        start = start.astimezone(timezone.utc)

    end = start + timedelta(hours=horizon_hours)

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation_probability,windspeed_10m,is_day",
        "timezone": "UTC",
        "forecast_days": 2,
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    hourly = data.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    pprob = hourly.get("precipitation_probability") or []
    wind = hourly.get("windspeed_10m") or []
    is_day = hourly.get("is_day") or []

    if not (len(times) == len(temps) == len(pprob) == len(wind) == len(is_day)) or len(times) == 0:
        # Defensive fallback if API shape changes or returns partial data
        raise RuntimeError("Unexpected Open-Meteo response format")

    selected = []
    for i, t in enumerate(times):
        dt = _parse_iso_utc(t)
        if start <= dt < end:
            # precipitation_probability can be null in some cases; treat as 0
            selected.append((
                float(temps[i]),
                float(pprob[i] if pprob[i] is not None else 0.0),
                float(wind[i]),
                float(is_day[i]),
            ))

    # If the selected window had no entries (rare), fall back to the first hour
    if not selected:
        selected = [(
            float(temps[0]),
            float(pprob[0] if pprob[0] is not None else 0.0),
            float(wind[0]),
            float(is_day[0]),
        )]

    n = len(selected)
    return WeatherSlice(
        temp_c=sum(v[0] for v in selected) / n,
        precip_prob=sum(v[1] for v in selected) / n,
        wind_kmh=sum(v[2] for v in selected) / n,
        is_day=sum(v[3] for v in selected) / n,
    )
