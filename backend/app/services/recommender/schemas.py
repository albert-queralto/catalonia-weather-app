from __future__ import annotations

import os
import sys
from pathlib import Path

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal
from uuid import UUID
from datetime import datetime

MAIN_PATH = str(Path(__file__).resolve().parents[3])
if MAIN_PATH not in sys.path:
    sys.path.append(MAIN_PATH)
    

from app.services.activity.schemas import GeoJSONPoint

EventType = Literal["view", "click", "save", "complete", "dismiss", "rate"]


class EventIn(BaseModel):
    """
    Client-logged event. For training quality, you should log impressions (view)
    server-side in /recommendations, but clients can send click/save/etc here.
    """
    model_config = ConfigDict(extra="forbid")
    activity_id: UUID
    event_type: EventType
    ts: Optional[datetime] = None

    request_id: Optional[UUID] = None
    position: Optional[int] = None

    user_lat: Optional[float] = None
    user_lon: Optional[float] = None

    weather_temp_c: Optional[float] = None
    weather_precip_prob: Optional[float] = None
    weather_wind_kmh: Optional[float] = None
    weather_is_day: Optional[float] = None
    
    rating: Optional[int] = None  # For explicit user ratings (e.g. 1-5 stars)


class ActivityOut(BaseModel):
    """
    API response payload for a recommended activity.
    """
    id: UUID
    name: str
    category: str
    tags: List[str] = Field(default_factory=list)

    indoor: bool
    covered: bool

    price_level: int
    difficulty: int
    duration_minutes: int

    distance_km: float
    score: float
    reason: str

    recommendation_label: Optional[str] = None
    recommendation_group: Optional[str] = None
    
    best_start: Optional[datetime] = None
    best_end: Optional[datetime] = None
    
    base_score: Optional[float] = None
    
    alert_severity: int = 0
    alert_meteors: List[str] = Field(default_factory=list)
    
    air_quality_score: Optional[float] = None
    air_quality_pm2_5: Optional[float] = None
    air_quality_pm10: Optional[float] = None
    air_quality_no2: Optional[float] = None
    air_quality_ozone: Optional[float] = None
    air_quality_uv_index: Optional[float] = None

    location: GeoJSONPoint
    created_at: datetime
    validated: bool

    request_id: Optional[UUID] = None
    position: Optional[int] = None
    weather_temp_c: Optional[float] = None
    weather_precip_prob: Optional[float] = None
    weather_wind_kmh: Optional[float] = None
    weather_is_day: Optional[float] = None
    rating: Optional[int] = None  # For explicit user ratings (e.g. 1-5 stars)
