from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import joblib
import numpy as np
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.recommender.features import build_features, reason_text, ActivityRow

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
        except FileNotFoundError:
            self.model = None
            self.feature_order = []
        except Exception as e:
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


def fetch_candidates(db: Session, lat: float, lon: float, radius_km: float) -> List[ActivityRow]:
    q = text("""
      SELECT
        id::text, name, category, tags, indoor, covered,
        price_level, difficulty, duration_minutes,
        ST_Y(location::geometry) AS lat,
        ST_X(location::geometry) AS lon
      FROM activities
      WHERE ST_DWithin(location, ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography, :meters)
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
        )
        s = model.score(feats)
        scored.append((s, feats["distance_km"], a, feats))

    scored.sort(key=lambda x: x[0], reverse=True)

    results: List[dict] = []
    for s, dist, a, feats in scored[:limit]:
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
            "score": float(s),
            "reason": reason_text(a, weather_precip_prob, weather_temp_c),
        })
    return results
