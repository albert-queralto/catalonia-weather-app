# Catalunya Weather (React + FastAPI + Redis + PostGIS + Celery/RabbitMQ)

Catalunya-focused weather web app that started as a hobby project.

## Stack
- **Frontend:** React (Vite) + Leaflet + MUI + Recharts + TypeScript
- **Backend:** FastAPI (Python, async)
- **Cache:** Redis
- **DB:** Postgres + PostGIS (SQLAlchemy async + GeoAlchemy2)
- **Jobs:** Celery worker + Celery Beat (broker: RabbitMQ)

## Features

- Interactive Catalonia map with:
  - Real-time air quality data (Open-Meteo API) visualized by station, with colormap overlays and comarques boundaries.
  - Weather station data (Meteocat) and variable selection.
  - Modal popups with hourly air quality charts (Recharts).
  - Hover tooltips for station markers.
  - Comarques boundaries overlay (GeoJSON, materialized view, and caching for performance).
  - Episodis Oberts (warnings) map with period selection and colored overlays.
- Backend API:
  - Endpoints for current and hourly air quality, weather, radar, and comarques lookup.
  - Materialized view and caching for fast comarques GeoJSON.
  - Async data fetching, pandas DataFrame processing, and robust schema alignment.
- Celery periodic tasks for data refresh, caching, and notification evaluation.

## Quickstart
```bash
cp .env.example .env
docker compose up --build
```

Backend:
- Health: http://localhost:4000/api/health
- Docs: http://localhost:4000/api/docs

Frontend:
- http://localhost:5173

RabbitMQ management UI:
- http://localhost:15672 (admin/admin)

## Database migration + sample comarca load
```bash
docker compose exec api alembic upgrade head
docker compose exec api python scripts/load_comarcas.py
```
The sample GeoJSON includes the 42 comarques of Catalonia (Spain).

## Key endpoints

### Weather & Air Quality
- `GET /api/v1/meteocat/stations` — List all Meteocat stations.
- `GET /api/v1/air-quality?lat=..&lon=..` — Current air quality for a location.
- `GET /api/v1/air-quality/hourly?lat=..&lon=..` — Hourly air quality for a location.

### Comarcas & Geo
- `GET /api/v1/comarcas/geojson` — GeoJSON of all comarcas (optimized, cached).
- `GET /api/v1/comarcas/lookup?lat=..&lon=..` — Find comarca by coordinates.
- `GET /api/v1/forecast/comarca/lookup?lat=..&lon=..` — Forecast by comarca.

### Radar
- `GET /api/v1/radar/timestamps`
- `GET /api/v1/radar/tiles/{timestamp}/{z}/{x}/{y}.png`

### Episodis Oberts (Warnings)
- `GET /api/v1/meteocat/episodis-oberts` — List of current warnings, with affected comarques and periods.

## Frontend Features

- `/` — Main dashboard with Catalonia map, air quality, and weather overlays.
- Air Quality Map: Select parameter, see colormap, hover for tooltip, click for hourly modal.
- Episodis Oberts Map: See warnings by period, colored overlays, and tooltips.
- Responsive UI with MUI and Recharts.

## Backend Features

- FastAPI async endpoints, robust error handling, and schema validation.
- Materialized view for comarcas (EPSG:4326) for fast spatial queries.
- Redis caching for GeoJSON and other heavy endpoints.
- Data ingestion and transformation with pandas.
- Celery tasks for periodic data refresh and notification rule evaluation.

## Celery periodic tasks
Celery Beat runs:
- Refresh radar timestamps
- Refresh alerts
- Cache comarca forecasts (hourly)

The schedules can be adjusted in `backend/app/workers/celery_app.py`.

---

**Development notes:**
- All code is type-checked and linted.
- See `frontend/src/components/AirQualityMap.tsx` and `frontend/src/components/EpisodisOberts.tsx` for main map logic.
- See `backend/app/api/v1/endpoints/` for all API routes.
- See `backend/app/services/air_quality/service.py` for air quality data logic.