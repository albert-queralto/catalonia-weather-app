from __future__ import annotations

import json
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Optional

import httpx

from app.core.config import settings
from app.services.forecast.schemas import ComarcaDailyPoint, ComarcaForecastResponse, ForecastResponse


def _parse_date(v) -> Optional[date]:
    if not v:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        try:
            return date.fromisoformat(v[:10])
        except Exception:
            return None
    return None


def _as_float(v) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None


def _as_int(v) -> Optional[int]:
    try:
        if v is None:
            return None
        return int(float(v))
    except Exception:
        return None


class MeteocatClient:
    """Meteocat integration with a practical hobby-mode.

    - Comarca daily forecasts: implemented in a way that works with a sample payload immediately.
    - Real API: plug your URL template when you know the exact dataset endpoint/format.

    Notes:
    - Meteocat Open Data exposes multiple products; this client keeps *your* surface stable.
    """

    def __init__(self):
        self.use_sample = str(getattr(settings, "meteocat_use_sample", "1")).strip() not in {"0", "false", "False"}
        self.url_template = (getattr(settings, "meteocat_comarca_forecast_url_template", "") or "").strip()

    async def fetch_comarca_forecast(
        self, comarca_code: str, date_obj: Optional[date] = None, tz: str = "Europe/Madrid"
    ) -> ComarcaForecastResponse:
        """
        Fetches comarca forecast from Meteocat Pronostic API for a given date.
        """
        if date_obj is None:
            date_obj = datetime.now().date()
        year = date_obj.year
        month = f"{date_obj.month:02d}"
        day = f"{date_obj.day:02d}"

        base_url = settings.meteocat_pronostic_base_url
        endpoint = f"/comarcal/{year}/{month}/{day}"
        url = f"{base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        # Extract values for this comarca
        max_temp = self._find_by_id(data.get("maximes", []), comarca_code)
        min_temp = self._find_by_id(data.get("minimes", []), comarca_code)
        
        # For "mati" and "tarda", extract relevant info
        mati = data.get("mati", {})
        tarda = data.get("tarda", {})

        mati_data = self._extract_period(mati, comarca_code)
        tarda_data = self._extract_period(tarda, comarca_code)

        # Compose daily points (one for the day, or one for each period if you want)
        daily = [
            ComarcaDailyPoint(
                date=date_obj,
                temperature_max_c=_as_float(max_temp.get("temperatura")) if max_temp else None,
                temperature_min_c=_as_float(min_temp.get("temperatura")) if min_temp else None,
                precipitation_probability_pct=_as_int(
                    (mati_data["precipitacio"] or {}).get("probabilitat")
                ),
                precipitation_sum_mm=_as_float(
                    (mati_data["precipitacio"] or {}).get("acumulacio")
                ),
                wind_gust_max_m_s=None,  # Not present in this response
                summary=None,  # You may want to map cel["simbol"] to a summary string
            ),
            ComarcaDailyPoint(
                date=date_obj,
                temperature_max_c=_as_float(max_temp.get("temperatura")) if max_temp else None,
                temperature_min_c=_as_float(min_temp.get("temperatura")) if min_temp else None,
                precipitation_probability_pct=_as_int(
                    (tarda_data["precipitacio"] or {}).get("probabilitat")
                ),
                precipitation_sum_mm=_as_float(
                    (tarda_data["precipitacio"] or {}).get("acumulacio")
                ),
                wind_gust_max_m_s=None,
                summary=None,
            ),
        ]

        return ComarcaForecastResponse(
            comarca_code=comarca_code,
            comarca_name=str(comarca_code),  # No name in this response
            timezone=tz,
            updated_at=datetime.now(timezone.utc),
            daily=daily,
        )

    def _extract_period(self, period, comarca_code):
        cel = self._find_by_id(period.get("cel", []), comarca_code)
        calamarsa = self._find_by_id(period.get("calamarsa", []), comarca_code)
        precipitacio = self._find_by_id(period.get("precipitacio", []), comarca_code)
        return {
            "cel": cel,
            "calamarsa": calamarsa,
            "precipitacio": precipitacio,
        }

    def _find_by_id(self, items, comarca_code, key="idComarca"):
        return next((item for item in items if str(item.get(key)) == str(comarca_code)), None)

    async def fetch_station_metadata(
        self, estat: str = "activa", data: Optional[str] = None
    ) -> list[dict]:
        """
        Fetches station metadata from Meteocat XEMA API.

        Args:
            estat: Station status (e.g., 'activa', 'baixa', etc.)
            data: Date in YYYY-MM-DD format (optional)

        Returns:
            List of station metadata dictionaries.
        """
        base_url = settings.meteocat_xema_base_url
        endpoint = "/estacions/metadades"
        params = {"estat": estat}
        if data:
            params["data"] = data

        url = f"{base_url}{endpoint}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()


meteocat_client = MeteocatClient()
