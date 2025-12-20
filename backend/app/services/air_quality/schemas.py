from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AirQualityPoint(BaseModel):
    time: datetime
    pm10: Optional[float] = None
    pm2_5: Optional[float] = None
    carbon_monoxide: Optional[float] = None
    carbon_dioxide: Optional[float] = None
    nitrogen_dioxide: Optional[float] = None
    sulphur_dioxide: Optional[float] = None
    ozone: Optional[float] = None
    uv_index: Optional[float] = None


class AirQualityResponse(BaseModel):
    updated_at: datetime
    lat: float
    lon: float
    provider: str
    observations: list[AirQualityPoint]
