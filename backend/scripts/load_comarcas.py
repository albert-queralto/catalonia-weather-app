from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings


DEFAULT_PATH = Path(__file__).resolve().parents[1] / "data" / "comarcas_sample.geojson"


async def main(path: Path) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    geo = json.loads(path.read_text(encoding="utf-8"))

    async with SessionLocal() as session:
        for feat in geo.get("features", []):
            props = feat.get("properties", {}) or {}
            geom = feat.get("geometry")
            if not geom:
                continue

            code = str(props.get("CODICOMAR") or "").strip()
            name = str(props.get("NOMCOMAR") or code).strip()

            if not code:
                continue

            # Upsert using raw SQL to keep it simple and avoid dialect gotchas.
            # ST_GeomFromGeoJSON expects a JSON string.
            await session.execute(
                text(
                    """
                    INSERT INTO comarcas (code, name, geom)
                    VALUES (:code, :name, ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326))
                    ON CONFLICT (code)
                    DO UPDATE SET name = EXCLUDED.name, geom = EXCLUDED.geom
                    """
                ),
                {"code": code, "name": name, "geojson": json.dumps(geom)},
            )
        await session.commit()

    await engine.dispose()
    print(f"Loaded comarcas from {path}")


if __name__ == "__main__":
    asyncio.run(main(DEFAULT_PATH))
