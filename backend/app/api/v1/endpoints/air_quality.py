from __future__ import annotations

from fastapi import APIRouter, Query, HTTPException
from app.services.air_quality.schemas import AirQualityResponse, AirQualityPoint
from app.services.air_quality.service import air_quality_service

router = APIRouter()
"""Endpoints for retrieving air quality data."""

@router.get("/air-quality", response_model=AirQualityResponse)
async def air_quality(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
) -> AirQualityResponse:
    """
    Get current air quality data for a specific latitude and longitude.

    Args:
        lat (float): Latitude of the location.
        lon (float): Longitude of the location.

    Returns:
        AirQualityResponse: Air quality data for the location.

    Raises:
        HTTPException: 404 if no data is available, 502 for service errors.
    """
    try:
        result = await air_quality_service.get_air_quality(lat=lat, lon=lon)
        if not result.observations or result.observations[0] is None:
            raise HTTPException(status_code=404, detail="No air quality data available for this location.")
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Air quality service error: {str(e)}")

@router.get("/air-quality/hourly", response_model=list[AirQualityPoint])
async def air_quality_hourly(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
) -> list[AirQualityPoint]:
    """
    Get hourly air quality data for a specific latitude and longitude.

    Args:
        lat (float): Latitude of the location.
        lon (float): Longitude of the location.

    Returns:
        list[AirQualityPoint]: List of hourly air quality data points.

    Raises:
        HTTPException: 404 if no data is available, 502 for service errors.
    """
    try:
        points = await air_quality_service.get_air_quality_hourly(lat=lat, lon=lon)
        if not points:
            raise HTTPException(status_code=404, detail="No hourly air quality data available for this location.")
        return points
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Air quality service error: {str(e)}")