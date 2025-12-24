from fastapi import APIRouter, Query
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

router = APIRouter()

# Setup Open-Meteo API client with cache and retry
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

@router.get("/openmeteo/hourly-forecast")
def get_hourly_forecast(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180)
):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": [
            "precipitation",
            "precipitation_probability",
            "apparent_temperature",
            "cloud_cover",
            "wind_speed_10m",
        ],
    }
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]

    hourly = response.Hourly()
    hourly_precipitation = hourly.Variables(0).ValuesAsNumpy()
    hourly_precipitation_probability = hourly.Variables(1).ValuesAsNumpy()
    hourly_apparent_temperature = hourly.Variables(2).ValuesAsNumpy()
    hourly_cloud_cover = hourly.Variables(3).ValuesAsNumpy()
    hourly_wind_speed_10m = hourly.Variables(4).ValuesAsNumpy()

    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        ).strftime("%Y-%m-%dT%H:%M:%SZ").tolist(),
        "precipitation": hourly_precipitation.tolist(),
        "precipitation_probability": hourly_precipitation_probability.tolist(),
        "apparent_temperature": hourly_apparent_temperature.tolist(),
        "cloud_cover": hourly_cloud_cover.tolist(),
        "wind_speed_10m": hourly_wind_speed_10m.tolist(),
    }

    # Return as a list of dicts for each hour
    result = [
        {
            "date": hourly_data["date"][i],
            "precipitation": hourly_data["precipitation"][i],
            "precipitation_probability": hourly_data["precipitation_probability"][i],
            "apparent_temperature": hourly_data["apparent_temperature"][i],
            "cloud_cover": hourly_data["cloud_cover"][i],
            "wind_speed_10m": hourly_data["wind_speed_10m"][i],
        }
        for i in range(len(hourly_data["date"]))
    ]
    return result