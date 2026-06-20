from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class StationSummaryOut(BaseModel):
    codi: str
    nom: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    altitud: Optional[int] = None
    comarca: Optional[str] = None


class StationVariableSummaryOut(BaseModel):
    codi: int
    nom: str
    unitat: str
    acronim: str
    tipus: str
    decimals: int


class StationValuePointOut(BaseModel):
    time: datetime
    value: float


class DailyStationStatOut(BaseModel):
    date: date
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    avg_value: Optional[float] = None
    count: int
    expected_count: int
    missing_count: int
    missing_pct: float


class MissingIntervalOut(BaseModel):
    starts_at: datetime
    ends_at: datetime
    gap_hours: float


class NearbyStationComparisonOut(BaseModel):
    codi: str
    nom: str
    distance_km: float
    avg_value: Optional[float] = None
    delta_vs_selected: Optional[float] = None


class SameDayLastYearOut(BaseModel):
    current_date: date
    current_avg: Optional[float] = None
    last_year_date: date
    last_year_avg: Optional[float] = None
    delta: Optional[float] = None


class WeekHistoricalAverageOut(BaseModel):
    current_week_start: date
    current_week_end: date
    current_avg: Optional[float] = None
    historical_avg: Optional[float] = None
    delta: Optional[float] = None
    years_used: int


class MicroclimateInsightOut(BaseModel):
    reference_station_code: str
    reference_station_name: str
    daypart: str
    avg_delta: Optional[float] = None
    sample_count: int
    text: str


class StationExplorerOut(BaseModel):
    station: StationSummaryOut
    variable: StationVariableSummaryOut

    points: List[StationValuePointOut] = Field(default_factory=list)
    daily_stats: List[DailyStationStatOut] = Field(default_factory=list)
    missing_intervals: List[MissingIntervalOut] = Field(default_factory=list)

    nearby_comparison: List[NearbyStationComparisonOut] = Field(default_factory=list)

    today_vs_same_day_last_year: Optional[SameDayLastYearOut] = None
    this_week_vs_historical_average: Optional[WeekHistoricalAverageOut] = None

    microclimate_insights: List[MicroclimateInsightOut] = Field(default_factory=list)


class ForecastAccuracyPointOut(BaseModel):
    time: datetime
    observed: float
    forecast: float
    error: float
    absolute_error: float


class ForecastAccuracySummaryOut(BaseModel):
    provider: str
    station_code: str
    metric: str
    lead_hours: int

    sample_count: int
    mae: Optional[float] = None
    rmse: Optional[float] = None
    bias: Optional[float] = None

    points: List[ForecastAccuracyPointOut] = Field(default_factory=list)