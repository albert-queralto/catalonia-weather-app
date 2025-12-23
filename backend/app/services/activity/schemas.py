from pydantic import BaseModel, Field
from datetime import date
from typing import List, Optional, Literal

class GeoJSONPoint(BaseModel):
    type: Literal["Point"]
    coordinates: List[float]  # [lon, lat]

class ActivitySuggestionBase(BaseModel):
    name: str
    category: str
    tags: List[str] = Field(default_factory=list)
    indoor: bool
    covered: bool
    price_level: int
    difficulty: int
    duration_minutes: int
    location: GeoJSONPoint
    created_at: Optional[date] = None

class ActivitySuggestionIn(ActivitySuggestionBase):
    pass

class ActivitySuggestionOut(ActivitySuggestionBase):
    id: str
    validated: bool

    class Config:
        orm_mode = True