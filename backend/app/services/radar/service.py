from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import httpx

from app.services.cache import cache


class RadarService:
    """Radar tile service.

    For hobby use, RainViewer provides simple timestamped tile URLs.
    If you switch to Meteocat XRAD or another provider later, keep the FastAPI surface stable.
    """

    # See RainViewer docs / examples; adapt as needed.
    API_URL = "https://api.rainviewer.com/public/weather-maps.json"
    TILE_BASE = "https://tile.rainviewer.com/v2/radar"  # /{timestamp}/256/{z}/{x}/{y}/2/1_1.png

    async def get_timestamps(self) -> dict:
        cache_key = "radar:v1:timestamps"
        cached = await cache.get_json(cache_key)
        if cached:
            return cached

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(self.API_URL)
            resp.raise_for_status()
            payload = resp.json()

        out = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "provider": "rainviewer",
            "timestamps": payload.get("radar", {}).get("past", []) + payload.get("radar", {}).get("nowcast", []),
        }
        await cache.set_json(cache_key, out, ttl_seconds=60 * 5)
        return out

    async def fetch_tile(self, z: int, x: int, y: int, timestamp: int) -> bytes:
        # Cache tiles aggressively; they are immutable per timestamp.
        cache_key = f"radar:v1:tile:{timestamp}:{z}:{x}:{y}"
        cached = await cache.get_json(cache_key)
        if cached and isinstance(cached, dict) and "b64" in cached:
            import base64

            return base64.b64decode(cached["b64"])

        url = f"{self.TILE_BASE}/{timestamp}/256/{z}/{x}/{y}/2/1_1.png"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content = resp.content

        # Store in cache as base64 JSON to keep Redis simple (binary safe alternative is redis.set bytes).
        import base64

        await cache.set_json(cache_key, {"b64": base64.b64encode(content).decode("ascii")}, ttl_seconds=60 * 60 * 24)
        return content


radar_service = RadarService()
