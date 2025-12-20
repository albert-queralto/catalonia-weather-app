from __future__ import annotations

from fastapi import APIRouter, Path
from fastapi.responses import Response

from app.services.radar.service import radar_service

router = APIRouter()


@router.get("/radar/timestamps")
async def radar_timestamps() -> dict:
    return await radar_service.get_timestamps()


@router.get("/radar/tiles/{timestamp}/{z}/{x}/{y}.png")
async def radar_tile(
    timestamp: int = Path(..., description="Radar frame timestamp"),
    z: int = Path(..., ge=0, le=20),
    x: int = Path(..., ge=0),
    y: int = Path(..., ge=0),
) -> Response:
    content = await radar_service.fetch_tile(z=z, x=x, y=y, timestamp=timestamp)
    return Response(content=content, media_type="image/png")
