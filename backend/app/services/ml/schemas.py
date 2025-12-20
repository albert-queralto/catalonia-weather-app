from __future__ import annotations

from datetime import datetime, date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CurrentConditions(BaseModel):
    time: datetime
    temperature_c: Optional[float] = None
    wind_speed_m_s: Optional[float] = None
    wind_gust_m_s: Optional[float] = None
    precipitation_mm: Optional[float] = None
    weather_code: Optional[int] = None


class HourlyPoint(BaseModel):
    time: datetime
    temperature_c: Optional[float] = None
    precipitation_mm: Optional[float] = None
    wind_speed_m_s: Optional[float] = None
    wind_gust_m_s: Optional[float] = None
    weather_code: Optional[int] = None


class DailyPoint(BaseModel):
    date: date
    temperature_max_c: Optional[float] = None
    temperature_min_c: Optional[float] = None
    precipitation_sum_mm: Optional[float] = None
    wind_gust_max_m_s: Optional[float] = None


class ForecastResponse(BaseModel):
    provider: Literal["open_meteo", "meteocat"]
    lat: float
    lon: float
    timezone: str

    updated_at: datetime = Field(..., description="When this response was produced by your API")
    current: Optional[CurrentConditions] = None
    hourly: list[HourlyPoint] = Field(default_factory=list)
    daily: list[DailyPoint] = Field(default_factory=list)


class ComarcaDailyPoint(BaseModel):
    date: date
    temperature_max_c: Optional[float] = None
    temperature_min_c: Optional[float] = None
    precipitation_probability_pct: Optional[int] = None
    precipitation_sum_mm: Optional[float] = None
    wind_gust_max_m_s: Optional[float] = None
    summary: Optional[str] = None


class ComarcaForecastResponse(BaseModel):
    provider: Literal["meteocat"] = "meteocat"
    comarca_code: str
    comarca_name: str
    timezone: str = "Europe/Madrid"

    updated_at: datetime = Field(..., description="When this response was produced by your API")
    daily: list[ComarcaDailyPoint] = Field(default_factory=list)
