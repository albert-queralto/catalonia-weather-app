from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import joblib
import numpy as np
from uuid import UUID
import hashlib
import random

from sqlalchemy.orm import Session
from sqlalchemy import text, bindparam

from app.services.air_quality.schemas import AirQualityPoint
from app.services.air_quality.health import label_european_aqi
from app.services.recommender.features import (
    ActivityRow,
    WeatherHour,
    WeatherSlice,
    aggregate_weather_slice,
    build_features,
    reason_text,
    recommendation_label,
)
from app.services.recommender.feature_contract import ensure_feature_contract, FEATURE_COLUMNS
from app.services.recommender.features import classify_weather_condition


@dataclass(frozen=True)
class AlertContext:
    severity: int = 0
    meteors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class AirQualityWindow:
    pm2_5: Optional[float] = None
    pm10: Optional[float] = None
    nitrogen_dioxide: Optional[float] = None
    ozone: Optional[float] = None
    uv_index: Optional[float] = None

    european_aqi: Optional[float] = None
    health_label: str = "unknown"
    health_advice: str = "Air-quality data is not available."
    dominant_pollutant: Optional[str] = None

    # 0 = good, 1 = bad. Use this for penalties.
    score: float = 0.0


class MLRecommender:
    """
    Thin wrapper around a saved model artifact.

    Expected joblib payload:
      {
        "model": <sklearn-like model with predict_proba>,
        "feature_order": [<feature1>, <feature2>, ...]
      }
    """
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        self.feature_order: List[str] = []
        self._loaded_mtime: Optional[float] = None

    def _model_mtime(self) -> Optional[float]:
        try:
            return Path(self.model_path).stat().st_mtime
        except OSError:
            return None

    def confidence_from_score(self, score: float) -> float:
        if self.model is None:
            return 0.35

        p = max(0.0, min(1.0, float(score)))
        return float(abs(p - 0.5) * 2.0)

    def load(self) -> None:
        mtime = self._model_mtime()
        try:
            payload = joblib.load(self.model_path)
            self.model = payload["model"]
            self.feature_order = list(payload["feature_order"])
            
            if self.feature_order != FEATURE_COLUMNS:
                raise ValueError(f"Model feature order {self.feature_order} does not match expected {FEATURE_COLUMNS}")

            self._loaded_mtime = mtime
                
        except FileNotFoundError:
            self.model = None
            self.feature_order = []
            self._loaded_mtime = None
        except Exception:
            # Fail closed: keep fallback scoring
            self.model = None
            self.feature_order = []
            self._loaded_mtime = mtime

    def load_if_stale(self) -> None:
        if self._model_mtime() != self._loaded_mtime:
            self.load()

    def score(self, features: Dict[str, float]) -> float:
        """
        Returns a score used for ranking.
        If model loaded: probability of positive outcome (click/save/complete).
        Otherwise: heuristic fallback.
        """
        self.load_if_stale()

        if self.model is None or not self.feature_order:
            # Simple fallback heuristic
            base = 0.0
            base += 2.0 * float(features.get("cat_weight", 0.0))
            base += 0.5 * float(features.get("tag_overlap", 0.0))
            base -= 0.15 * float(features.get("distance_km", 0.0))
            base -= 1.0 * float(features.get("precip_penalty", 0.0))
            base -= 0.5 * float(features.get("wind_penalty", 0.0))
            return float(base)

        x = np.array([[float(features.get(k, 0.0)) for k in self.feature_order]], dtype=float)

        # Most LightGBM/sklearn classifiers support predict_proba
        if hasattr(self.model, "predict_proba"):
            p = self.model.predict_proba(x)[0, 1]
            return float(p)

        # If not available, fall back to predict and cast
        if hasattr(self.model, "predict"):
            p = self.model.predict(x)[0]
            return float(p)

        # Absolute fallback
        return 0.0

def assign_ranking_strategy(user_id: UUID, request_id: UUID) -> str:
    raw = f"{user_id}:{request_id}".encode("utf-8")
    bucket = int(hashlib.sha256(raw).hexdigest(), 16) % 100

    if bucket < 70:
        return "baseline"
    if bucket < 90:
        return "epsilon_10"
    return "epsilon_20"


def exploration_rate_for_strategy(strategy: str) -> float:
    if strategy == "epsilon_10":
        return 0.10
    if strategy == "epsilon_20":
        return 0.20
    return 0.0


def apply_exploration(
    ranked: List[dict],
    *,
    limit: int,
    strategy: str,
    user_id: UUID,
    request_id: UUID,
) -> List[dict]:
    epsilon = exploration_rate_for_strategy(strategy)

    if epsilon <= 0 or len(ranked) <= limit:
        selected = ranked[:limit]
        for row in selected:
            row["exploration_bucket"] = "exploit"
        return selected

    exploit_n = max(1, int(limit * (1.0 - epsilon)))
    explore_n = limit - exploit_n

    exploit = ranked[:exploit_n]
    pool = ranked[exploit_n:]

    rng = random.Random(f"{user_id}:{request_id}:{strategy}")

    pool = sorted(
        pool,
        key=lambda row: (
            row.get("activity_view_count", 0.0),
            row.get("created_at", ""),
        ),
    )

    explore = rng.sample(pool, k=min(explore_n, len(pool)))

    for row in exploit:
        row["exploration_bucket"] = "exploit"

    for row in explore:
        row["exploration_bucket"] = "explore"

    return exploit + explore

def get_user_preferences(db: Session, user_id: UUID) -> Tuple[Dict[str, float], Dict[str, float]]:
    q = text("SELECT category, weight FROM user_preferences WHERE user_id = :uid")
    rows = db.execute(q, {"uid": str(user_id)}).fetchall()
    cat = {r[0]: float(r[1]) for r in rows}

    q2 = text("""
      SELECT unnest(a.tags) AS tag, count(*) AS cnt
      FROM events e
      JOIN activities a ON a.id = e.activity_id
      WHERE e.user_id = :uid AND e.event_type IN ('save','complete')
      GROUP BY 1
    """)
    rows2 = db.execute(q2, {"uid": str(user_id)}).fetchall()
    tag = {r[0]: float(r[1]) for r in rows2}
    return cat, tag

def get_user_stats(db: Session, user_id: UUID) -> Dict[str, float]:
    q = text("""
        SELECT
            COUNT(*) AS total_events,
            COUNT(DISTINCT e.activity_id) AS unique_activities,
            AVG(e.rating) AS user_avg_rating,
            SUM(CASE WHEN e.event_type IN ('click','save','complete') THEN 1 ELSE 0 END) AS user_engagement_count,

            AVG(CASE WHEN e.event_type = 'complete' THEN a.duration_minutes END) AS user_avg_completed_duration,

            AVG(
            CASE
                WHEN e.event_type = 'dismiss'
                AND (
                    COALESCE(e.weather_precip_prob, 0) >= 40
                    OR COALESCE(e.weather_wind_kmh, 0) >= 30
                    OR COALESCE(e.air_quality_score, 0) >= 60
                    OR COALESCE(e.uv_index, 0) >= 6
                )
                THEN 1.0
                WHEN e.event_type = 'dismiss' THEN 0.0
            END
            ) AS user_bad_weather_dismiss_rate

        FROM events e
        LEFT JOIN activities a ON a.id = e.activity_id
        WHERE e.user_id = :uid
        """)
    r = db.execute(q, {"uid": str(user_id)}).fetchone()
    total_events = float(r[0] or 0)
    unique_activities = float(r[1] or 0)
    user_avg_rating = float(r[2] or 2.5)
    user_engagement_count = float(r[3] or 0)
    user_exploration_rate = (unique_activities / total_events) if total_events > 0 else 0.0
    user_avg_completed_duration = float(r[4] or 60.0)
    user_bad_weather_dismiss_rate = float(r[5] or 0.0)

    return {
        "total_events": total_events,
        "unique_activities": unique_activities,
        "user_avg_rating": user_avg_rating,
        "user_engagement_count": user_engagement_count,
        "user_exploration_rate": user_exploration_rate,
        "user_avg_completed_duration": user_avg_completed_duration,
        "user_bad_weather_dismiss_rate": user_bad_weather_dismiss_rate,
    }
    
def get_activity_stats_batch(
    db: Session,
    activity_ids: List[UUID],
    weather_condition: str | None = None,
) -> Dict[str, Dict[str, float]]:
    if not activity_ids:
        return {}
    
    q = text("""
        SELECT
            activity_id::text AS activity_id,
            SUM(CASE WHEN event_type = 'view' THEN 1 ELSE 0 END) AS activity_view_count,
            AVG(rating) AS activity_avg_rating,
            SUM(CASE WHEN event_type IN ('click','save','complete') THEN 1 ELSE 0 END) AS activity_engagement_count,

            SUM(
            CASE
                WHEN event_type = 'view'
                AND (:weather_condition IS NULL OR weather_condition = :weather_condition)
                THEN 1 ELSE 0
            END
            ) AS activity_weather_view_count,

            SUM(
            CASE
                WHEN event_type IN ('click','save','complete')
                AND (:weather_condition IS NULL OR weather_condition = :weather_condition)
                THEN 1 ELSE 0
            END
            ) AS activity_weather_engagement_count

        FROM events
        WHERE activity_id IN :activity_ids
        GROUP BY activity_id
        """).bindparams(bindparam("activity_ids", expanding=True))
    
    rows = db.execute(
        q,
        {
            "activity_ids": activity_ids,
            "weather_condition": weather_condition,
        },
    ).fetchall()
    out: Dict[str, Dict[str, float]] = {}
    for r in rows:
        activity_id = r[0]
        activity_view_count = float(r[1] or 0)
        activity_avg_rating = float(r[2] or 2.5)
        activity_engagement_count = float(r[3] or 0)
        activity_engagement_rate = (activity_engagement_count / activity_view_count) if activity_view_count > 0 else 0.0
        activity_weather_view_count = float(r[4] or 0)
        activity_weather_engagement_count = float(r[5] or 0)
        activity_weather_engagement_rate = (
            activity_weather_engagement_count / activity_weather_view_count
            if activity_weather_view_count > 0
            else 0.0
        )
        out[activity_id] = {
            "activity_view_count": activity_view_count,
            "activity_avg_rating": activity_avg_rating,
            "activity_engagement_count": activity_engagement_count,
            "activity_engagement_rate": activity_engagement_rate,
            "activity_weather_view_count": activity_weather_view_count,
            "activity_weather_engagement_count": activity_weather_engagement_count,
            "activity_weather_engagement_rate": activity_weather_engagement_rate,
        }

    return out

def fetch_candidates(db: Session, lat: float, lon: float, radius_km: float) -> List[ActivityRow]:
    q = text("""
      SELECT
        id::text, name, category, tags, indoor, covered,
        price_level, difficulty, duration_minutes,
        ST_Y(location::geometry) AS lat,
        ST_X(location::geometry) AS lon,
        validated, created_at,
        opening_hours
      FROM activities
      WHERE ST_DWithin(location, ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography, :meters)
      AND validated = true
      LIMIT 500
    """)
    meters = radius_km * 1000.0
    rows = db.execute(q, {"lat": lat, "lon": lon, "meters": meters}).fetchall()

    out: List[ActivityRow] = []
    for r in rows:
        out.append(ActivityRow(
            id=r[0],
            name=r[1],
            category=r[2],
            tags=list(r[3] or []),
            indoor=bool(r[4]),
            covered=bool(r[5]),
            price_level=int(r[6]),
            difficulty=int(r[7]),
            duration_minutes=int(r[8]),
            lat=float(r[9]),
            lon=float(r[10]),
            validated=bool(r[11]),
            created_at=r[12],
            opening_hours=r[13],
        ))
    return out


def build_scoring_windows(
    weather_points: List[WeatherHour],
    *,
    horizon_hours: int,
    planning_hours: int,
    stride_hours: int = 3,
) -> List[WeatherSlice]:
    """
    Creates rolling scoring windows:
    now, +3h, +6h, +9h, ...
    """
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    latest_start = now + timedelta(hours=max(0, planning_hours - horizon_hours))

    windows: List[WeatherSlice] = []
    start = now

    while start <= latest_start:
        windows.append(
            aggregate_weather_slice(
                weather_points,
                start=start,
                horizon_hours=horizon_hours,
            )
        )
        start += timedelta(hours=stride_hours)

    return windows


def _avg(values: List[Optional[float]]) -> Optional[float]:
    clean = [float(v) for v in values if v is not None]
    return sum(clean) / len(clean) if clean else None


def _normalize_threshold(value: Optional[float], good: float, bad: float) -> float:
    """
    Maps pollutant value to 0..1.
    0 means okay, 1 means bad for recommendations.
    """
    if value is None:
        return 0.0
    if value <= good:
        return 0.0
    if value >= bad:
        return 1.0

    return (value - good) / (bad - good)


def aggregate_air_quality_window(
    points: List[AirQualityPoint],
    *,
    start: datetime,
    horizon_hours: int,
) -> AirQualityWindow:
    """
    Aggregates hourly air quality data for the same time window
    used by the weather recommender.
    """
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    start = start.astimezone(timezone.utc)
    end = start + timedelta(hours=horizon_hours)

    selected: List[AirQualityPoint] = []

    for p in points:
        ts = p.time
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        ts = ts.astimezone(timezone.utc)

        if start <= ts < end:
            selected.append(p)

    if not selected and points:
        selected = [
            min(
                points,
                key=lambda p: abs(
                    (
                        (
                            p.time.replace(tzinfo=timezone.utc)
                            if p.time.tzinfo is None
                            else p.time.astimezone(timezone.utc)
                        )
                        - start
                    ).total_seconds()
                ),
            )
        ]

    pm2_5 = _avg([p.pm2_5 for p in selected])
    pm10 = _avg([p.pm10 for p in selected])
    no2 = _avg([p.nitrogen_dioxide for p in selected])
    ozone = _avg([p.ozone for p in selected])
    uv = _avg([p.uv_index for p in selected])
    european_aqi = _avg([p.european_aqi for p in selected])
    health = label_european_aqi(european_aqi)

    pollutant_score = max(
        _normalize_threshold(pm2_5, 10, 25),
        _normalize_threshold(pm10, 20, 50),
        _normalize_threshold(no2, 25, 80),
        _normalize_threshold(ozone, 80, 140),
        _normalize_threshold(uv, 3, 8),
    )

    return AirQualityWindow(
        pm2_5=pm2_5,
        pm10=pm10,
        nitrogen_dioxide=no2,
        ozone=ozone,
        uv_index=uv,
        european_aqi=european_aqi,
        health_label=health.label,
        health_advice=health.advice,
        dominant_pollutant=health.dominant_pollutant,
        score=pollutant_score,
    )


def activity_air_quality_exposure(activity: ActivityRow) -> float:
    """
    Determines how strongly an activity should be penalized by pollution / UV.

    Indoor activity: almost no exposure.
    Outdoor sport / nature: high exposure.
    Covered activity: medium exposure.
    """
    if activity.indoor:
        return 0.05

    tags = {t.strip().lower() for t in activity.tags}
    exposure = 0.65

    if activity.category in {"Sport", "Nature"}:
        exposure = 1.0

    if tags & {"hiking", "running", "cycling", "fitness", "outdoor", "water", "family"}:
        exposure = max(exposure, 0.9)

    if activity.covered:
        exposure *= 0.65

    return exposure


def choose_group(activity: ActivityRow, distance_km: float, label: str) -> str:
    """
    Groups recommendations for the UI.
    """
    tags = {t.strip().lower() for t in activity.tags}

    if label == "Indoor alternative recommended" or activity.indoor:
        return "Indoor backup"

    if "family" in tags or activity.difficulty <= 1:
        return "Family-friendly"

    if activity.price_level <= 1 or "free" in tags or "budget-friendly" in tags:
        return "Free/low cost"

    if activity.duration_minutes <= 90 and distance_km <= 3:
        return "Short activities nearby"

    return "Best outdoor"


def diversify(
    scored: List[dict],
    limit: int,
    max_per_category: int = 5,
    max_per_group: int = 8,
) -> List[dict]:
    """
    Prevents the API from returning 20 almost identical activities.
    """
    selected: List[dict] = []
    by_category: Dict[str, int] = {}
    by_group: Dict[str, int] = {}

    for item in scored:
        category = item["category"]
        group = item["recommendation_group"]

        if by_category.get(category, 0) >= max_per_category:
            continue

        if by_group.get(group, 0) >= max_per_group:
            continue

        selected.append(item)
        by_category[category] = by_category.get(category, 0) + 1
        by_group[group] = by_group.get(group, 0) + 1

        if len(selected) >= limit:
            break

    if len(selected) < limit:
        seen = {r["id"] for r in selected}

        for item in scored:
            if item["id"] in seen:
                continue

            selected.append(item)

            if len(selected) >= limit:
                break

    return selected


def recommend(
    db: Session,
    model: MLRecommender,
    user_id: UUID,
    lat: float,
    lon: float,
    radius_km: float,
    weather_temp_c: Optional[float] = None,
    weather_precip_prob: Optional[float] = None,
    weather_wind_kmh: Optional[float] = None,
    weather_is_day: Optional[float] = None,
    limit: int = 20,
    *,
    request_id: Optional[UUID] = None,
    ranking_strategy: Optional[str] = None,
    weather_windows: Optional[List[WeatherSlice]] = None,
    air_quality_points: Optional[List[AirQualityPoint]] = None,
    alert_context: Optional[AlertContext] = None,
    sensitive_to_air_quality: bool = False,
) -> List[dict]:
    cat_pref, tag_pref = get_user_preferences(db, user_id)
    candidates = fetch_candidates(db, lat, lon, radius_km)

    request_id = request_id or UUID(int=0)
    ranking_strategy = ranking_strategy or assign_ranking_strategy(user_id, request_id)

    if not candidates:
        return []

    user_stats = get_user_stats(db, user_id)
    activity_ids = [UUID(a.id) for a in candidates]
    activity_stats_cache: Dict[str, Dict[str, Dict[str, float]]] = {}

    def stats_for_condition(condition: str) -> Dict[str, Dict[str, float]]:
        if condition not in activity_stats_cache:
            activity_stats_cache[condition] = get_activity_stats_batch(
                db,
                activity_ids,
                weather_condition=condition,
            )
        return activity_stats_cache[condition]

    if not weather_windows:
        now = datetime.now(timezone.utc)

        weather_windows = [
            WeatherSlice(
                temp_c=float(weather_temp_c or 0.0),
                precip_prob=float(weather_precip_prob or 0.0),
                wind_kmh=float(weather_wind_kmh or 0.0),
                is_day=float(weather_is_day if weather_is_day is not None else 1.0),
                starts_at=now,
                ends_at=now + timedelta(hours=4),
                apparent_temp_c=float(weather_temp_c or 0.0) if weather_temp_c is not None else 0.0,
            )
        ]

    alert_context = alert_context or AlertContext()
    air_quality_points = air_quality_points or []

    scored: List[dict] = []

    for activity in candidates:
        exposure = activity_air_quality_exposure(activity)

        if sensitive_to_air_quality:
            exposure *= 1.4

        window_scores: List[dict] = []

        for window in weather_windows:
            window_start = window.starts_at or datetime.now(timezone.utc)
            window_end = window.ends_at or window_start + timedelta(hours=4)
            window_hours = max(
                1,
                int((window_end - window_start).total_seconds() / 3600),
            )

            aq = aggregate_air_quality_window(
                air_quality_points,
                start=window_start,
                horizon_hours=window_hours,
            )

            aq_european_aqi = float(aq.european_aqi or 0.0)
            uv_index = float(aq.uv_index or 0.0)
            ozone = float(aq.ozone or 0.0)

            weather_condition = classify_weather_condition(
                temp_c=window.temp_c,
                precip_prob=window.precip_prob,
                wind_kmh=window.wind_kmh,
                uv_index=uv_index,
                air_quality_score=aq_european_aqi,
            )
            
            activity_stats = stats_for_condition(weather_condition).get(activity.id, {})
            
            features = build_features(
                user_pref=cat_pref,
                user_tag_pref=tag_pref,
                activity=activity,
                user_lat=lat,
                user_lon=lon,
                weather_temp_c=window.temp_c,
                weather_precip_prob=window.precip_prob,
                weather_wind_kmh=window.wind_kmh,
                weather_is_day=window.is_day,
                apparent_temp_c=window.apparent_temp_c,
                uv_index=uv_index,
                air_quality_score=aq_european_aqi,
                ozone=ozone,
                alert_severity=alert_context.severity,
                now=window_start,
                user_stats=user_stats,
                activity_stats=activity_stats,
            )

            features = ensure_feature_contract(features)
            base_score = model.score(features)

            air_quality_penalty = exposure * aq.score * 0.45

            alert_penalty = 0.0

            if alert_context.severity > 0 and not activity.indoor:
                alert_penalty = min(10.0, 0.35 * alert_context.severity)

                # Hard constraint for dangerous warnings.
                # Outdoor activities become fallback options only.
                if alert_context.severity >= 4:
                    alert_penalty = 10.0

            final_score = float(base_score - air_quality_penalty - alert_penalty)

            window_scores.append(
                {
                    "score": final_score,
                    "base_score": float(base_score),
                    "features": features,
                    "weather": window,
                    "air_quality": aq,
                    "starts_at": window_start,
                    "ends_at": window_end,
                    "air_quality_penalty": air_quality_penalty,
                    "alert_penalty": alert_penalty,
                    "weather_condition": weather_condition,
                }
            )

        now_window = window_scores[0]
        best_window = max(window_scores, key=lambda x: x["score"])
        model_confidence = model.confidence_from_score(best_window["base_score"])

        best_weather: WeatherSlice = best_window["weather"]
        best_aq: AirQualityWindow = best_window["air_quality"]
        best_features = best_window["features"]

        label = recommendation_label(
            now_score=now_window["score"],
            best_score=best_window["score"],
            best_start=best_window["starts_at"],
            indoor=activity.indoor,
            alert_severity=alert_context.severity,
        )

        group = choose_group(
            activity,
            float(best_features["distance_km"]),
            label,
        )

        scored.append(
            {
                "id": activity.id,
                "name": activity.name,
                "category": activity.category,
                "tags": activity.tags,
                "indoor": activity.indoor,
                "covered": activity.covered,
                "price_level": activity.price_level,
                "difficulty": activity.difficulty,
                "duration_minutes": activity.duration_minutes,
                "distance_km": float(best_features["distance_km"]),
                "location": {
                    "type": "Point",
                    "coordinates": [activity.lon, activity.lat],
                },
                "validated": activity.validated,
                "created_at": activity.created_at.isoformat(),
                "score": float(best_window["score"]),
                "base_score": float(best_window["base_score"]),
                "reason": reason_text(
                    activity,
                    distance_km=float(best_features["distance_km"]),
                    cat_weight=float(best_features.get("cat_weight", 0.0)),
                    tag_overlap=float(best_features.get("tag_overlap", 0.0)),
                    weather_precip_prob=best_weather.precip_prob,
                    weather_temp_c=best_weather.temp_c,
                    weather_wind_kmh=best_weather.wind_kmh,
                    air_quality_score=best_aq.score,
                    pm2_5=best_aq.pm2_5,
                    pm10=best_aq.pm10,
                    nitrogen_dioxide=best_aq.nitrogen_dioxide,
                    ozone=best_aq.ozone,
                    uv_index=best_aq.uv_index,
                    alert_severity=alert_context.severity,
                    alert_meteors=list(alert_context.meteors),
                    best_start=best_window["starts_at"],
                ),
                "recommendation_label": label,
                "recommendation_group": group,
                "best_start": best_window["starts_at"].isoformat(),
                "best_end": best_window["ends_at"].isoformat() if best_window["ends_at"] else None,
                "alert_severity": alert_context.severity,
                "alert_meteors": list(alert_context.meteors),
                "air_quality_pm2_5": best_aq.pm2_5,
                "air_quality_pm10": best_aq.pm10,
                "air_quality_no2": best_aq.nitrogen_dioxide,
                "air_quality_ozone": best_aq.ozone,
                "air_quality_uv_index": best_aq.uv_index,
                "position": 0,
                "weather_temp_c": best_features.get("weather_temp_c", 0.0),
                "weather_precip_prob": best_features.get("weather_precip_prob", 0.0),
                "weather_wind_kmh": best_features.get("weather_wind_kmh", 0.0),
                "weather_is_day": best_features.get("weather_is_day", 1.0),
                "activity_view_count": float(best_features.get("activity_view_count", 0.0)),
                "apparent_temp_c": float(best_weather.apparent_temp_c),
                "uv_index": float(best_aq.uv_index or 0.0),
                "ozone": float(best_aq.ozone or 0.0),

                "air_quality_score": float(best_aq.european_aqi or 0.0),
                "air_quality_risk_score": float(best_aq.score),
                "air_quality_label": best_aq.health_label,
                "air_quality_advice": best_aq.health_advice,

                "weather_condition": best_window.get("weather_condition", "unknown"),

                "model_confidence": model_confidence,
                "confidence_label": (
                    "high" if model_confidence >= 0.65
                    else "medium" if model_confidence >= 0.35
                    else "low"
                ),
                "ranking_strategy": ranking_strategy,
                "exploration_bucket": "exploit",
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)

    diverse_ranked = diversify(scored, limit=max(limit * 2, limit))
    results = apply_exploration(
        diverse_ranked,
        limit=limit,
        strategy=ranking_strategy,
        user_id=user_id,
        request_id=request_id,
    )

    for rank, row in enumerate(results, start=1):
        row["position"] = rank

    return results
