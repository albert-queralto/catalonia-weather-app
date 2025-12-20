from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Comarca
@dataclass(frozen=True)
class ComarcaLookupResult:
    code: str
    name: str


class ComarcaService:
    async def list_comarcas(self, session: AsyncSession) -> list[ComarcaLookupResult]:
        res = await session.execute(select(Comarca.code, Comarca.name).order_by(Comarca.name.asc()))
        return [ComarcaLookupResult(code=r[0], name=r[1]) for r in res.all()]

    async def lookup_by_point(self, session: AsyncSession, lat: float, lon: float) -> Optional[ComarcaLookupResult]:
        # PostGIS uses (lon, lat)
        point = func.ST_SetSRID(func.ST_Point(lon, lat), 4326)
        stmt = (
            select(Comarca.code, Comarca.name)
            .where(func.ST_Contains(Comarca.geom, point))
            .limit(1)
        )
        res = await session.execute(stmt)
        row = res.first()
        if not row:
            return None
        return ComarcaLookupResult(code=row[0], name=row[1])


comarca_service = ComarcaService()
