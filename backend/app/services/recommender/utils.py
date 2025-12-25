import os
import requests
import pandas as pd

API_PORT = os.getenv("API_PORT", "4000")

def get_weather_for_event(lat: float, lon: float, event_time: str):
    """
    Fetch hourly weather data and match to the event_time (ISO string).
    Returns a dict with weather fields for the closest hour.
    """
    url = f"http://localhost:{API_PORT}/api/v1/openmeteo/hourly-forecast"
    params = {"latitude": lat, "longitude": lon}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()

    # Find the closest hour
    closest = min(data, key=lambda x: abs(pd.Timestamp(x["date"]) - pd.Timestamp(event_time)))
    return {
        "weather_temp_c": closest["apparent_temperature"],
        "weather_precip_prob": closest["precipitation_probability"],
        "weather_wind_kmh": closest["wind_speed_10m"],
        "weather_is_day": 1 if 6 <= pd.Timestamp(closest["date"]).hour < 20 else 0,  # crude day/night
        "cloud_cover": closest["cloud_cover"],
        "precipitation": closest["precipitation"],
    }