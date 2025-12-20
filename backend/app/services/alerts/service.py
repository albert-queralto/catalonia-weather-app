import os
import httpx
from app.services.alerts.schemas import EpisodiObert

class AlertsService:
    async def get_episodis_oberts(self, year: int, month: int, day: int) -> list[EpisodiObert]:
        url = (
            f"https://api.meteo.cat/pronostic/v2/smp/episodis-oberts"
            f"?data={year:04d}-{month:02d}-{day:02d}Z"
        )
        api_key = os.environ.get("METEOCAT_API_KEY")
        headers = {"x-api-key": api_key} if api_key else {}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return [EpisodiObert.model_validate(ep) for ep in data]

alerts_service = AlertsService()