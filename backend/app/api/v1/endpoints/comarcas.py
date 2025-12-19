from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json

from app.db.session import get_session
from app.services.geo.schemas import ComarcaOut
from app.services.geo.service import comarca_service

router = APIRouter()


@router.get("/comarcas", response_model=list[ComarcaOut])
async def list_comarcas(session: AsyncSession = Depends(get_session)) -> list[ComarcaOut]:
    rows = await comarca_service.list_comarcas(session=session)
    return [ComarcaOut(code=r.code, name=r.name) for r in rows]


@router.get("/comarcas/lookup", response_model=ComarcaOut | None)
async def lookup_comarca(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    session: AsyncSession = Depends(get_session),
) -> ComarcaOut | None:
    # Use a spatial query to find the comarca containing the point
    result = await session.execute(
        text("""
            SELECT code, name
            FROM comarcas
            WHERE ST_Contains(
                geom,
                ST_SetSRID(ST_Point(:lon, :lat), 4326)
            )
            LIMIT 1
        """),
        {"lon": lon, "lat": lat}
    )
    row = result.first()
    if not row:
        return None
    return ComarcaOut(code=row.code, name=row.name)


@router.get("/comarcas/geojson")
async def comarcas_geojson(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        text("SELECT code, name, ST_AsGeoJSON(ST_Transform(geom, 4326)) as geojson FROM comarcas")
    )
    features = []
    for row in result.fetchall():
        features.append({
            "type": "Feature",
            "geometry": json.loads(row.geojson),
            "properties": {
                "code": row.code,
                "name": row.name,
            }
        })
    return {
        "type": "FeatureCollection",
        "features": features
    }