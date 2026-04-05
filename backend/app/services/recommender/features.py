from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime, timedelta, timezone
from app.services.recommender.feature_contract import ensure_feature_contract

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
    validated: bool
    created_at: datetime


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in kilometers between two lat/lon points."""
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat / 2.0) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2.0) ** 2
    c = 2.0 * atan2(sqrt(a), sqrt(1.0 - a))
    return R * c

def normalize_tag(tag: str) -> str:
    """Normalize tags for consistent matching."""
    return tag.strip().lower()

def compute_tag_overlap(activity_tags: Sequence[str], user_tag_pref: Dict[str, float]) -> float:
    """Compute a simple tag overlap score between activity tags and user tag preferences."""
    if not activity_tags or not user_tag_pref:
        return 0.0
    
    normalized_pref = {normalize_tag(k) for k in user_tag_pref.keys()}
    overlap = 0.0
    for tag in activity_tags:
        if normalize_tag(tag) in normalized_pref:
            overlap += 1.0
    return overlap

@dataclass(frozen=True)
class WeatherPenalties:
    precip_penalty: float
    wind_penalty: float
    cold_penalty: float
    heat_penalty: float
    

def compute_weather_penalties(
    *,
    indoor: bool,
    covered: bool,
    weather_precip_prob: float,
    weather_wind_kmh: float,
    weather_temp_c: float
) -> WeatherPenalties:
    outdoor_exposure = 0.0 if indoor else (0.35 if covered else 1.0)
    
    precip_penalty = outdoor_exposure * (weather_precip_prob / 100.0)
    wind_penalty = outdoor_exposure * (weather_wind_kmh / 50.0)
    cold_penalty = outdoor_exposure * max(0.0, (10.0 - weather_temp_c) / 10.0)
    heat_penalty = outdoor_exposure * max(0.0, (weather_temp_c - 30.0) / 10.0)

    return WeatherPenalties(
        precip_penalty=precip_penalty,
        wind_penalty=wind_penalty,
        cold_penalty=cold_penalty,
        heat_penalty=heat_penalty
    )

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
    *,
    position: float = 0.0,
    now: Optional[datetime] = None,
    user_stats: Optional[Dict[str, float]] = None,
    activity_stats: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    if now is None:
        now = datetime.now(timezone.utc)

    user_stats = user_stats or {}
    activity_stats = activity_stats or {}

    distance = haversine_km(user_lat, user_lon, activity.lat, activity.lon)
    cat_weight = float(user_pref.get(activity.category, 0.0))

    tag_overlap = compute_tag_overlap(activity.tags, user_tag_pref)

    indoor_f = 1.0 if activity.indoor else 0.0
    covered_f = 1.0 if activity.covered else 0.0
    price_level_f = float(activity.price_level)
    difficulty_f = float(activity.difficulty)
    duration_minutes_f = float(activity.duration_minutes)

    penalties = compute_weather_penalties(
        indoor=activity.indoor,
        covered=activity.covered,
        weather_precip_prob=weather_precip_prob,
        weather_wind_kmh=weather_wind_kmh,
        weather_temp_c=weather_temp_c
    )

    hour_of_day = float(now.hour)
    day_of_week = float(now.weekday())
    is_weekend = 1.0 if now.weekday() >= 5 else 0.0

    raw = {
        "distance_km": distance,
        "cat_weight": cat_weight,
        "tag_overlap": tag_overlap,

        "indoor_f": indoor_f,
        "covered_f": covered_f,
        "price_level_f": price_level_f,
        "difficulty_f": difficulty_f,
        "duration_minutes_f": duration_minutes_f,

        "weather_temp_c": float(weather_temp_c),
        "weather_precip_prob": float(weather_precip_prob),
        "weather_wind_kmh": float(weather_wind_kmh),
        "weather_is_day": float(weather_is_day),

        "precip_penalty": penalties.precip_penalty,
        "wind_penalty": penalties.wind_penalty,
        "cold_penalty": penalties.cold_penalty,
        "heat_penalty": penalties.heat_penalty,

        "position": float(position),

        "hour_of_day": hour_of_day,
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,

        "temp_distance_interaction": float(weather_temp_c) * distance,
        "price_distance_interaction": price_level_f * distance,
        "cat_weight_distance": cat_weight * distance,
        "indoor_precip": indoor_f * float(weather_precip_prob),

        "total_events": float(user_stats.get("total_events", 0.0)),
        "unique_activities": float(user_stats.get("unique_activities", 0.0)),
        "user_avg_rating": float(user_stats.get("user_avg_rating", 2.5)),
        "user_engagement_count": float(user_stats.get("user_engagement_count", 0.0)),
        "user_exploration_rate": float(user_stats.get("user_exploration_rate", 0.0)),

        "activity_view_count": float(activity_stats.get("activity_view_count", 0.0)),
        "activity_avg_rating": float(activity_stats.get("activity_avg_rating", 2.5)),
        "activity_engagement_count": float(activity_stats.get("activity_engagement_count", 0.0)),
        "activity_engagement_rate": float(activity_stats.get("activity_engagement_rate", 0.0)),
    }

    return ensure_feature_contract(raw)


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
                float(temps[i] if temps[i] is not None else 0.0),
                float(pprob[i] if pprob[i] is not None else 0.0),
                float(wind[i] if wind[i] is not None else 0.0),
                float(is_day[i] if is_day[i] is not None else 0.0),
            ))

    # If the selected window had no entries (rare), fall back to the first hour
    if not selected:
        nearest_idx = min(
            range(len(times)),
            key=lambda idx: abs((_parse_iso_utc(times[idx]) - start).total_seconds())
        )
        
        selected = [(
            float(temps[nearest_idx] if temps[nearest_idx] is not None else 0.0),
            float(pprob[nearest_idx] if pprob[nearest_idx] is not None else 0.0),
            float(wind[nearest_idx] if wind[nearest_idx] is not None else 0.0),
            float(is_day[nearest_idx] if is_day[nearest_idx] is not None else 0.0),
        )]

    n = len(selected)
    temp_c = sum(x[0] for x in selected) / n
    precip_prob = sum(x[1] for x in selected) / n
    wind_kmh = sum(x[2] for x in selected) / n
    is_day = sum(x[3] for x in selected) / n
    
    return WeatherSlice(
        temp_c=float(temp_c),
        precip_prob=float(precip_prob),
        wind_kmh=float(wind_kmh),
        is_day=float(is_day),
    )
