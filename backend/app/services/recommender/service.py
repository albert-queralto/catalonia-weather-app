from __future__ import annotations

from typing import Dict, List, Tuple
import joblib
import numpy as np
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text, bindparam

from app.services.recommender.features import build_features, reason_text, ActivityRow
from app.services.recommender.feature_contract import ensure_feature_contract, FEATURE_COLUMNS


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

    def load(self) -> None:
        try:
            payload = joblib.load(self.model_path)
            self.model = payload["model"]
            self.feature_order = list(payload["feature_order"])
            
            if self.feature_order != FEATURE_COLUMNS:
                raise ValueError(f"Model feature order {self.feature_order} does not match expected {FEATURE_COLUMNS}")
                
        except FileNotFoundError:
            self.model = None
            self.feature_order = []
        except Exception:
            # Fail closed: keep fallback scoring
            self.model = None
            self.feature_order = []

    def score(self, features: Dict[str, float]) -> float:
        """
        Returns a score used for ranking.
        If model loaded: probability of positive outcome (click/save/complete).
        Otherwise: heuristic fallback.
        """
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
        COUNT(DISTINCT activity_id) AS unique_activities,
        AVG(rating) AS user_avg_rating,
        SUM(CASE WHEN event_type IN ('click','save','complete') THEN 1 ELSE 0 END) AS user_engagement_count
      FROM events
      WHERE user_id = :uid
    """)
    r = db.execute(q, {"uid": str(user_id)}).fetchone()
    total_events = float(r[0] or 0)
    unique_activities = float(r[1] or 0)
    user_avg_rating = float(r[2] or 2.5)
    user_engagement_count = float(r[3] or 0)
    user_exploration_rate = (unique_activities / total_events) if total_events > 0 else 0.0

    return {
        "total_events": total_events,
        "unique_activities": unique_activities,
        "user_avg_rating": user_avg_rating,
        "user_engagement_count": user_engagement_count,
        "user_exploration_rate": user_exploration_rate,
    }
    
def get_activity_stats_batch(db: Session, activity_ids: List[UUID]) -> Dict[str, Dict[str, float]]:
    if not activity_ids:
        return {}
    
    q = text("""
      SELECT
        activity_id::text AS activity_id,
        SUM(CASE WHEN event_type = 'view' THEN 1 ELSE 0 END) AS activity_view_count,
        AVG(rating) AS activity_avg_rating,
        SUM(CASE WHEN event_type IN ('click','save','complete') THEN 1 ELSE 0 END) AS activity_engagement_count
      FROM events
        WHERE activity_id IN :activity_ids
        GROUP BY activity_id
    """).bindparams(bindparam("activity_ids", expanding=True))
    
    rows = db.execute(q, {"activity_ids": activity_ids}).fetchall()
    out: Dict[str, Dict[str, float]] = {}
    for r in rows:
        activity_id = r[0]
        activity_view_count = float(r[1] or 0)
        activity_avg_rating = float(r[2] or 2.5)
        activity_engagement_count = float(r[3] or 0)
        activity_engagement_rate = (activity_engagement_count / activity_view_count) if activity_view_count > 0 else 0.0
        out[activity_id] = {
            "activity_view_count": activity_view_count,
            "activity_avg_rating": activity_avg_rating,
            "activity_engagement_count": activity_engagement_count,
            "activity_engagement_rate": activity_engagement_rate,
        }

    return out

def fetch_candidates(db: Session, lat: float, lon: float, radius_km: float) -> List[ActivityRow]:
    q = text("""
      SELECT
        id::text, name, category, tags, indoor, covered,
        price_level, difficulty, duration_minutes,
        ST_Y(location::geometry) AS lat,
        ST_X(location::geometry) AS lon,
        validated, created_at
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
        ))
    return out


def recommend(
    db: Session,
    model: MLRecommender,
    user_id: UUID,
    lat: float,
    lon: float,
    radius_km: float,
    weather_temp_c: float,
    weather_precip_prob: float,
    weather_wind_kmh: float,
    weather_is_day: float,
    limit: int = 20,
) -> List[dict]:
    cat_pref, tag_pref = get_user_preferences(db, user_id)
    candidates = fetch_candidates(db, lat, lon, radius_km)

    if not candidates:
        return []
    
    user_stats = get_user_stats(db, user_id)
    activity_stats_map = get_activity_stats_batch(db, [UUID(a.id) for a in candidates])

    scored = []
    for a in candidates:
        feats = build_features(
            user_pref=cat_pref,
            user_tag_pref=tag_pref,
            activity=a,
            user_lat=lat,
            user_lon=lon,
            weather_temp_c=weather_temp_c,
            weather_precip_prob=weather_precip_prob,
            weather_wind_kmh=weather_wind_kmh,
            weather_is_day=weather_is_day,
            user_stats=user_stats,
            activity_stats=activity_stats_map.get(UUID(a.id), {}),
        )
        feats = ensure_feature_contract(feats)
        s = model.score(feats)
        scored.append((s, feats["distance_km"], a, feats))

    scored.sort(key=lambda x: x[0], reverse=True)

    results: List[dict] = []
    for rank, (s, dist, a, feats) in enumerate(scored[:limit], start=1):
        results.append({
            "id": a.id,  # string UUID is fine; Pydantic will parse to UUID
            "name": a.name,
            "category": a.category,
            "tags": a.tags,
            "indoor": a.indoor,
            "covered": a.covered,
            "price_level": a.price_level,
            "difficulty": a.difficulty,
            "duration_minutes": a.duration_minutes,
            "distance_km": float(dist),
            "location": {
                "type": "Point",
                "coordinates": [a.lon, a.lat],
            },
            "validated": a.validated,
            "created_at": a.created_at.isoformat(),
            "score": float(s),
            "reason": reason_text(a, weather_precip_prob, weather_temp_c),
            "position": rank,
            "weather_temp_c": feats.get("weather_temp_c", 0.0),
            "weather_precip_prob": feats.get("weather_precip_prob", 0.0),
            "weather_wind_kmh": feats.get("weather_wind_kmh", 0.0),
            "weather_is_day": feats.get("weather_is_day", 1.0),
        })
    return results
