from __future__ import annotations

from typing import Dict, Iterable

FEATURE_COLUMNS = [
    # Core features
    "distance_km",
    "cat_weight",
    "tag_overlap",

    # Activity attributes
    "indoor_f",
    "covered_f",
    "price_level_f",
    "difficulty_f",
    "duration_minutes_f",

    # Weather context
    "weather_temp_c",
    "weather_precip_prob",
    "weather_wind_kmh",
    "weather_is_day",

    # Weather penalties
    "precip_penalty",
    "wind_penalty",
    "cold_penalty",
    "heat_penalty",

    # Positional
    "position",

    # Temporal features
    "hour_of_day",
    "day_of_week",
    "is_weekend",

    # Interaction features
    "temp_distance_interaction",
    "price_distance_interaction",
    "cat_weight_distance",
    "indoor_precip",

    # User history features
    "total_events",
    "unique_activities",
    "user_avg_rating",
    "user_engagement_count",
    "user_exploration_rate",

    # Activity popularity features
    "activity_view_count",
    "activity_avg_rating",
    "activity_engagement_count",
    "activity_engagement_rate",
]

DEFAULT_FEATURE_VALUES = {
    "distance_km": 0.0,
    "cat_weight": 0.0,
    "tag_overlap": 0.0,

    "indoor_f": 0.0,
    "covered_f": 0.0,
    "price_level_f": 0.0,
    "difficulty_f": 0.0,
    "duration_minutes_f": 0.0,

    "weather_temp_c": 0.0,
    "weather_precip_prob": 0.0,
    "weather_wind_kmh": 0.0,
    "weather_is_day": 1.0,

    "precip_penalty": 0.0,
    "wind_penalty": 0.0,
    "cold_penalty": 0.0,
    "heat_penalty": 0.0,

    "position": 0.0,

    "hour_of_day": 12.0,
    "day_of_week": 0.0,
    "is_weekend": 0.0,

    "temp_distance_interaction": 0.0,
    "price_distance_interaction": 0.0,
    "cat_weight_distance": 0.0,
    "indoor_precip": 0.0,

    "total_events": 0.0,
    "unique_activities": 0.0,
    "user_avg_rating": 2.5,
    "user_engagement_count": 0.0,
    "user_exploration_rate": 0.0,

    "activity_view_count": 0.0,
    "activity_avg_rating": 2.5,
    "activity_engagement_count": 0.0,
    "activity_engagement_rate": 0.0,
}


def ensure_feature_contract(raw: Dict[str, float]) -> Dict[str, float]:
    """
    Return a dict that contains exactly the contract feature set.
    Missing values get safe defaults.
    Extra keys are ignored.
    """
    return {
        col: float(raw.get(col, DEFAULT_FEATURE_VALUES[col]))
        for col in FEATURE_COLUMNS
    }


def assert_feature_columns_present(columns: Iterable[str]) -> None:
    current = list(columns)
    missing = [c for c in FEATURE_COLUMNS if c not in current]
    extra = [c for c in current if c not in FEATURE_COLUMNS]

    if missing or extra:
        raise ValueError(
            f"Feature contract mismatch. Missing={missing}, Extra={extra}"
        )