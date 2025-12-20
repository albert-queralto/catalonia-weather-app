from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.services.air_quality.schemas import AirQualityPoint, AirQualityResponse
from app.services.cache import cache

import openmeteo_requests
import numpy as np
import pandas as pd
import requests_cache
from retry_requests import retry
import asyncio

class AirQualityService:
    def __init__(self):
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        self.openmeteo = openmeteo_requests.Client(session=retry_session)

    async def get_air_quality(self, lat: float, lon: float) -> AirQualityResponse:
        cache_key = f"airq:v2:{round(lat,3)}:{round(lon,3)}"
        cached = await cache.get_json(cache_key)
        if cached:
            return AirQualityResponse.model_validate(cached)

        # Run the blocking Open-Meteo client in a thread
        df = await asyncio.get_event_loop().run_in_executor(
            None, self._fetch_hourly_dataframe, lat, lon
        )

        if df.empty:
            raise Exception("No air quality data returned from Open-Meteo.")

        # Find the row with the timestamp closest to now
        now = pd.Timestamp.utcnow()
        idx = (df["date"] - now).abs().idxmin()
        row = df.loc[idx]

        point = AirQualityPoint(
            time=row["date"].to_pydatetime(),
            pm2_5=row["pm2_5"],
            pm10=row["pm10"],
            carbon_monoxide=row["carbon_monoxide"],
            carbon_dioxide=row["carbon_dioxide"],
            nitrogen_dioxide=row["nitrogen_dioxide"],
            sulphur_dioxide=row["sulphur_dioxide"],
            ozone=row["ozone"],
            uv_index=row["uv_index"],
        )

        payload = AirQualityResponse(
            updated_at=datetime.now(timezone.utc),
            lat=lat,
            lon=lon,
            provider="open-meteo",
            observations=[point],
        )
        await cache.set_json(cache_key, payload.model_dump(mode="json"), ttl_seconds=60 * 30)
        return payload

    def _fetch_hourly_dataframe(self, lat: float, lon: float) -> pd.DataFrame:
        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": [
                "pm2_5", "pm10", "carbon_monoxide", "carbon_dioxide",
                "nitrogen_dioxide", "sulphur_dioxide", "ozone", "uv_index",
            ],
        }
        responses = air_quality_service.openmeteo.weather_api(url, params=params)
        response = responses[0]
        hourly = response.Hourly()
        hourly_pm2_5 = hourly.Variables(0).ValuesAsNumpy()
        hourly_pm10 = hourly.Variables(1).ValuesAsNumpy()
        hourly_carbon_monoxide = hourly.Variables(2).ValuesAsNumpy()
        hourly_carbon_dioxide = hourly.Variables(3).ValuesAsNumpy()
        hourly_nitrogen_dioxide = hourly.Variables(4).ValuesAsNumpy()
        hourly_sulphur_dioxide = hourly.Variables(5).ValuesAsNumpy()
        hourly_ozone = hourly.Variables(6).ValuesAsNumpy()
        hourly_uv_index = hourly.Variables(7).ValuesAsNumpy()

        hourly_data = {"date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        )}
        hourly_data["pm2_5"] = hourly_pm2_5
        hourly_data["pm10"] = hourly_pm10
        hourly_data["carbon_monoxide"] = hourly_carbon_monoxide
        hourly_data["carbon_dioxide"] = hourly_carbon_dioxide
        hourly_data["nitrogen_dioxide"] = hourly_nitrogen_dioxide
        hourly_data["sulphur_dioxide"] = hourly_sulphur_dioxide
        hourly_data["ozone"] = hourly_ozone
        hourly_data["uv_index"] = hourly_uv_index

        hourly_dataframe = pd.DataFrame(data=hourly_data)
        hourly_dataframe = hourly_dataframe.replace({np.nan: None, np.inf: None, -np.inf: None})

        return hourly_dataframe
    
    async def get_air_quality_hourly(self, lat: float, lon: float) -> list[AirQualityPoint]:
        cache_key = f"airq:hourly:{round(lat,3)}:{round(lon,3)}"
        cached = await cache.get_json(cache_key)
        if cached:
            return [AirQualityPoint.model_validate(row) for row in cached]

        df = await asyncio.get_event_loop().run_in_executor(
            None, self._fetch_hourly_dataframe, lat, lon
        )
        if df.empty:
            raise Exception("No air quality data returned from Open-Meteo.")

        points = []
        for _, row in df.iterrows():
            points.append(AirQualityPoint(
                time=row["date"].to_pydatetime(),
                pm2_5=row["pm2_5"],
                pm10=row["pm10"],
                carbon_monoxide=row["carbon_monoxide"],
                carbon_dioxide=row["carbon_dioxide"],
                nitrogen_dioxide=row["nitrogen_dioxide"],
                sulphur_dioxide=row["sulphur_dioxide"],
                ozone=row["ozone"],
                uv_index=row["uv_index"],
            ))
        # Cache as list of dicts
        await cache.set_json(cache_key, [p.model_dump(mode="json") for p in points], ttl_seconds=60 * 30)
        return points

air_quality_service = AirQualityService()