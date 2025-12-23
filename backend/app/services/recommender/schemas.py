from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from uuid import UUID
from datetime import datetime

EventType = Literal["view", "click", "save", "complete", "dismiss"]


class EventIn(BaseModel):
    """
    Client-logged event. For training quality, you should log impressions (view)
    server-side in /recommendations, but clients can send click/save/etc here.
    """
    user_id: UUID
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

    request_id: Optional[UUID] = None
