from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime, timedelta, timezone
from app.services.recommender.feature_contract import ensure_feature_contract

from math import radians, sin, cos, sqrt, atan2, ceil
from zoneinfo import ZoneInfo

import httpx


CATALONIA_TZ = ZoneInfo("Europe/Madrid")


@dataclass(frozen=True)
class ActivityRow:
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
    opening_hours: Optional[dict] = None


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
    
def classify_weather_condition(
    temp_c: float,
    precip_prob: float,
    wind_kmh: float,
    uv_index: float = 0.0,
    air_quality_score: float = 0.0,
) -> str:
    if precip_prob >= 60:
        return "rainy"
    if wind_kmh >= 35:
        return "windy"
    if temp_c <= 8:
        return "cold"
    if temp_c >= 30:
        return "hot"
    if uv_index >= 6:
        return "high_uv"
    if air_quality_score >= 60:
        return "polluted"
    return "mild"


def estimate_transport_time_min(distance_km: float, mode: str = "walking") -> float:
    speeds = {
        "walking": 4.5,
        "cycling": 14.0,
        "driving": 35.0,
        "public_transport": 20.0,
    }
    speed = speeds.get(mode, 4.5)
    return float((distance_km / speed) * 60.0)


def season_from_month(month: int) -> float:
    # 0=winter, 1=spring, 2=summer, 3=autumn
    if month in (12, 1, 2):
        return 0.0
    if month in (3, 4, 5):
        return 1.0
    if month in (6, 7, 8):
        return 2.0
    return 3.0


def is_ozone_season(month: int) -> bool:
    return month in (5, 6, 7, 8, 9)


def compute_ozone_penalty(
    *,
    indoor: bool,
    ozone: float,
    month: int,
    hour: int,
) -> float:
    if indoor:
        return 0.0

    if not is_ozone_season(month):
        return 0.0

    # Tropospheric ozone tends to matter most for outdoor activity in warm daylight hours.
    daylight_peak = 1.0 if 11 <= hour <= 18 else 0.5

    if ozone <= 100:
        return 0.0
    if ozone <= 130:
        return 0.25 * daylight_peak
    if ozone <= 180:
        return 0.6 * daylight_peak
    return 1.0 * daylight_peak

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
    apparent_temp_c: float = 0.0,
    uv_index: float = 0.0,
    air_quality_score: float = 0.0,
    ozone: float = 0.0,
    alert_severity: int = 0,
    transport_mode: str = "walking",
    is_school_holiday: bool = False,
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
    transport_time_min = estimate_transport_time_min(distance, transport_mode)
    month = now.month
    season = season_from_month(month)
    is_evening = 1.0 if 18 <= now.hour <= 23 else 0.0
    is_open_now = is_open_at(activity.opening_hours, now)
    ozone_season = 1.0 if is_ozone_season(month) else 0.0
    ozone_penalty = compute_ozone_penalty(
        indoor=activity.indoor,
        ozone=ozone,
        month=month,
        hour=now.hour,
    )
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
        weather_temp_c=weather_temp_c,
        weather_precip_prob=weather_precip_prob,
        weather_wind_kmh=weather_wind_kmh,
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
        "apparent_temp_c": float(apparent_temp_c),
        "uv_index": float(uv_index),
        "air_quality_score": float(air_quality_score),
        "ozone": float(ozone),
        "alert_severity": float(alert_severity),

        "is_open_now": float(is_open_now),
        "transport_time_min": float(transport_time_min),

        "month": float(month),
        "season": float(season),
        "is_evening": float(is_evening),
        "is_school_holiday": 1.0 if is_school_holiday else 0.0,

        "user_avg_completed_duration": float(user_stats.get("user_avg_completed_duration", 60.0)),
        "user_bad_weather_dismiss_rate": float(user_stats.get("user_bad_weather_dismiss_rate", 0.0)),

        "activity_weather_view_count": float(activity_stats.get("activity_weather_view_count", 0.0)),
        "activity_weather_engagement_rate": float(activity_stats.get("activity_weather_engagement_rate", 0.0)),

        "ozone_season": ozone_season,
        "ozone_penalty": ozone_penalty,
        
        "outdoor_aq_risk": (1.0 - indoor_f) * float(air_quality_score),
        "outdoor_uv_risk": (1.0 - indoor_f) * float(uv_index),
        "outdoor_alert_risk": (1.0 - indoor_f) * float(alert_severity),
    }

    return ensure_feature_contract(raw)


def reason_text(
    activity: ActivityRow,
    *,
    distance_km: float,
    cat_weight: float,
    tag_overlap: float,
    weather_precip_prob: float,
    weather_temp_c: float,
    weather_wind_kmh: float,
    air_quality_score: float = 0.0,
    pm2_5: Optional[float] = None,
    pm10: Optional[float] = None,
    nitrogen_dioxide: Optional[float] = None,
    ozone: Optional[float] = None,
    uv_index: Optional[float] = None,
    alert_severity: int = 0,
    alert_meteors: Optional[List[str]] = None,
    best_start: Optional[datetime] = None,
) -> str:
    positives: List[str] = []
    negatives: List[str] = []

    pp = float(weather_precip_prob)
    t = float(weather_temp_c)
    wind = float(weather_wind_kmh)

    if activity.indoor:
        positives.append("it is indoors")
    elif activity.covered:
        positives.append("it is covered")

    if pp < 25:
        positives.append("rain probability is low")
    elif pp >= 45 and not activity.indoor:
        negatives.append("rain probability is high")

    if 12 <= t <= 28:
        positives.append("temperature is comfortable")
    elif t < 8 and not activity.indoor:
        negatives.append("it is cold")
    elif t > 32 and not activity.indoor:
        negatives.append("it is very hot")

    if wind > 40 and not activity.indoor:
        negatives.append("wind is strong")

    if air_quality_score < 0.25:
        positives.append("air quality is good")
    elif not activity.indoor:
        pollutant_bits = []

        if pm2_5 is not None and pm2_5 >= 15:
            pollutant_bits.append(f"PM2.5 {pm2_5:.0f}")
        if pm10 is not None and pm10 >= 45:
            pollutant_bits.append(f"PM10 {pm10:.0f}")
        if nitrogen_dioxide is not None and nitrogen_dioxide >= 40:
            pollutant_bits.append(f"NO₂ {nitrogen_dioxide:.0f}")
        if ozone is not None and ozone >= 100:
            pollutant_bits.append(f"O₃ {ozone:.0f}")
        if uv_index is not None and uv_index >= 6:
            pollutant_bits.append(f"UV {uv_index:.0f}")

        detail = f" ({', '.join(pollutant_bits)})" if pollutant_bits else ""
        negatives.append(f"moderate air quality{detail}")

    if alert_severity > 0:
        meteor_text = ", ".join(alert_meteors or [])
        warning = f"active Meteocat warning level {alert_severity}"
        if meteor_text:
            warning += f" for {meteor_text}"
        negatives.append(warning)

    positives.append(f"it is {distance_km:.1f} km away")

    if cat_weight > 0:
        positives.append(f"you often save {activity.category} activities")
    elif tag_overlap > 0:
        positives.append("it matches tags you have saved before")

    if negatives:
        text = "Not ideal now: " + "; ".join(negatives[:3]) + "."
        if best_start:
            text += f" Better after {_fmt_local_hour(best_start)}."
        return text

    return "Recommended because " + ", ".join(positives[:5]) + "."


def _fmt_local_hour(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CATALONIA_TZ).strftime("%H:%M")


def _daypart(dt: datetime) -> str:
    h = dt.astimezone(CATALONIA_TZ).hour
    
    if 5 <= h < 12:
        return "morning"
    elif 12 <= h < 18:
        return "afternoon"
    elif 18 <= h < 23:
        return "evening"
    return "night"


def recommendation_label(
    *,
    now_score: float,
    best_score: float,
    best_start: datetime,
    indoor: bool,
    alert_severity: int,
) -> str:
    """
    Produces short UI labels:
    - Best now
    - Better after 18:00
    - Avoid tomorrow morning
    - Indoor alternative recommended
    """
    delta_hours = (best_start - datetime.now(timezone.utc)).total_seconds() / 3600.0

    if alert_severity >= 4 and not indoor:
        return "Indoor alternative recommended"

    if best_score < 0.20 and not indoor:
        return f"Avoid {_daypart(best_start)}"

    if delta_hours <= 2 and best_score >= now_score - 0.03:
        return "Best now"

    if best_score > now_score + 0.08:
        return f"Better after {_fmt_local_hour(best_start)}"

    return "Good option"


@dataclass(frozen=True)
class WeatherHour:
    """One hourly forecast point, normalized to UTC."""
    time: datetime
    temp_c: float
    apparent_temp_c: float
    precip_prob: float
    wind_kmh: float
    is_day: float


@dataclass(frozen=True)
class WeatherSlice:
    temp_c: float
    apparent_temp_c: float
    precip_prob: float
    wind_kmh: float
    is_day: float
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    

def _parse_iso_utc(ts: str) -> datetime:
    # Open-Meteo returns ISO timestamps, usually without timezone; we use UTC.
    # Example: "2025-12-23T14:00"
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def fetch_weather_timeline(
    lat: float,
    lon: float,
    planning_hours: int = 48,
    start: Optional[datetime] = None,
) -> List[WeatherHour]:
    """
    Fetch hourly weather points for the next 24-48h so we can score several
    possible activity windows.
    """
    if planning_hours <= 0:
        raise ValueError("planning_hours must be > 0")
    
    if start is None:
        start = datetime.now(timezone.utc)
    elif start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    
    start = start.astimezone(timezone.utc)
    end = start + timedelta(hours=planning_hours)
    
    url = "https://api.open-meteo.com/v1/forecast"
    forecast_days = max(1, min(16, ceil(planning_hours / 24) + 1))
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,apparent_temperature,precipitation_probability,windspeed_10m,is_day",
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
    apparent = hourly.get("apparent_temperature") or []
    pprob = hourly.get("precipitation_probability") or []
    wind = hourly.get("windspeed_10m") or []
    is_day = hourly.get("is_day") or []
    
    if not (len(times) == len(temps) == len(apparent) == len(pprob) == len(wind) == len(is_day)) or len(times) == 0:
        raise RuntimeError("Unexpected Open-Meteo response format")
    
    points: List[WeatherHour] = []
    
    for i, t in enumerate(times):
        dt = _parse_iso_utc(t)
        if start <= dt < end:
            points.append(
                WeatherHour(
                    time=dt,
                    temp_c=float(temps[i] if temps[i] is not None else 0.0),
                    precip_prob=float(pprob[i] if pprob[i] is not None else 0.0),
                    wind_kmh=float(wind[i] if wind[i] is not None else 0.0),
                    is_day=float(is_day[i] if is_day[i] is not None else 0.0),
                    apparent_temp_c=float(apparent[i] if apparent[i] is not None else 0.0),
                )
            )
    
    if not points:
        nearest_idx = min(
            range(len(times)),
            key=lambda idx: abs((_parse_iso_utc(times[idx]) - start).total_seconds()),
        )
        points = [
            WeatherHour(
                time=_parse_iso_utc(times[nearest_idx]),
                temp_c=float(temps[nearest_idx] if temps[nearest_idx] is not None else 0.0),
                precip_prob=float(pprob[nearest_idx] if pprob[nearest_idx] is not None else 0.0),
                wind_kmh=float(wind[nearest_idx] if wind[nearest_idx] is not None else 0.0),
                is_day=float(is_day[nearest_idx] if is_day[nearest_idx] is not None else 0.0),
                apparent_temp_c=float(apparent[nearest_idx] if apparent[nearest_idx] is not None else 0.0),
            )
        ]

    return points


def aggregate_weather_slice(
    points: List[WeatherHour],
    start: datetime,
    horizon_hours: int,
) -> WeatherSlice:
    """
    Converts hourly weather points into one aggregated activity window.
    Example: 15:00–19:00 if horizon_hours=4.
    """
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    start = start.astimezone(timezone.utc)
    end = start + timedelta(hours=horizon_hours)

    selected = [p for p in points if start <= p.time < end]

    if not selected:
        selected = [min(points, key=lambda p: abs((p.time - start).total_seconds()))]

    n = len(selected)

    return WeatherSlice(
        temp_c=sum(p.temp_c for p in selected) / n,
        precip_prob=sum(p.precip_prob for p in selected) / n,
        wind_kmh=sum(p.wind_kmh for p in selected) / n,
        is_day=sum(p.is_day for p in selected) / n,
        starts_at=start,
        ends_at=end,
        apparent_temp_c=sum(p.apparent_temp_c for p in selected) / n,
    )


async def fetch_weather_slice(
    lat: float,
    lon: float,
    horizon_hours: int = 4,
    start: Optional[datetime] = None,
) -> WeatherSlice:
    """
    Backward-compatible helper.
    Existing code can still request one weather window.
    """
    if start is None:
        start = datetime.now(timezone.utc)
    elif start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    
    start = start.astimezone(timezone.utc)
    
    points = await fetch_weather_timeline(
        lat,
        lon,
        planning_hours=horizon_hours + 1,
        start=start,
    )
    
    return aggregate_weather_slice(points, start, horizon_hours)


def is_open_at(opening_hours: dict | None, now: datetime) -> float:
    if not opening_hours:
        return 1.0

    keys = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    day_key = keys[now.weekday()]
    intervals = opening_hours.get(day_key, [])

    current = now.strftime("%H:%M")

    for start, end in intervals:
        if start <= current <= end:
            return 1.0

    return 0.0