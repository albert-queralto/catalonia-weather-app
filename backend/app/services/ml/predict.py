import os
import httpx

METEOCAT_API_KEY = os.getenv("METEOCAT_API_KEY")
METEOCAT_BASE_URL = "https://api.meteo.cat/pronostic/v1"

async def fetch_comarcal_forecast(year: int, month: int, day: int):
    url = f"{METEOCAT_BASE_URL}/comarcal/{year:04d}/{month:02d}/{day:02d}"
    headers = {"x-api-key": METEOCAT_API_KEY}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()