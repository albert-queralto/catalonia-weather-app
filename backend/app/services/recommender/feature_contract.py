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
    
    "apparent_temp_c",
    "uv_index",
    "air_quality_score",
    "ozone",
    "alert_severity",

    "is_open_now",
    "transport_time_min",

    "month",
    "season",
    "is_evening",
    "is_school_holiday",

    "user_avg_completed_duration",
    "user_bad_weather_dismiss_rate",

    "activity_weather_view_count",
    "activity_weather_engagement_rate",

    "ozone_season",
    "ozone_penalty",
    
    "outdoor_aq_risk",
    "outdoor_uv_risk",
    "outdoor_alert_risk",
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
    
    "apparent_temp_c": 0.0,
    "uv_index": 0.0,
    "air_quality_score": 0.0,
    "ozone": 0.0,
    "alert_severity": 0.0,

    "is_open_now": 1.0,
    "transport_time_min": 0.0,

    "month": 1.0,
    "season": 0.0,
    "is_evening": 0.0,
    "is_school_holiday": 0.0,

    "user_avg_completed_duration": 60.0,
    "user_bad_weather_dismiss_rate": 0.0,

    "activity_weather_view_count": 0.0,
    "activity_weather_engagement_rate": 0.0,

    "ozone_season": 0.0,
    "ozone_penalty": 0.0,
    
    "outdoor_aq_risk": 0.0,
    "outdoor_uv_risk": 0.0,
    "outdoor_alert_risk": 0.0,
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