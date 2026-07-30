import os
import httpx

from app.services.cache import cache
from app.services.alerts.schemas import EpisodiObert

FRESH_CACHE_TTL_SECONDS = 30 * 60
STALE_CACHE_TTL_SECONDS = 3 * 24 * 60 * 60


def _cache_key(year: int, month: int, day: int, *, stale: bool = False) -> str:
    suffix = "stale" if stale else "fresh"
    return f"meteocat:smp:episodis-oberts:{year:04d}-{month:02d}-{day:02d}:{suffix}"


def _parse_episodes(data: list[dict]) -> list[EpisodiObert]:
    return [EpisodiObert.model_validate(ep) for ep in data]


class AlertsService:
    async def get_episodis_oberts(self, year: int, month: int, day: int) -> list[EpisodiObert]:
        cached = await cache.get_json(_cache_key(year, month, day))
        if cached is not None:
            return _parse_episodes(cached)

        url = (
            f"https://api.meteo.cat/pronostic/v2/smp/episodis-oberts"
            f"?data={year:04d}-{month:02d}-{day:02d}Z"
        )
        api_key = os.environ.get("METEOCAT_API_KEY")
        headers = {"x-api-key": api_key} if api_key else {}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                stale = await cache.get_json(_cache_key(year, month, day, stale=True))
                if stale is not None:
                    return _parse_episodes(stale)
            raise

        await cache.set_json(
            _cache_key(year, month, day),
            data,
            ttl_seconds=FRESH_CACHE_TTL_SECONDS,
        )
        await cache.set_json(
            _cache_key(year, month, day, stale=True),
            data,
            ttl_seconds=STALE_CACHE_TTL_SECONDS,
        )
        return _parse_episodes(data)

alerts_service = AlertsService()
