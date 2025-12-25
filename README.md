# Catalunya Weather (React + FastAPI + Redis + PostGIS + Celery/RabbitMQ)

A full-stack web application focused on Catalonia, providing real-time weather, air quality, warning data with interactive maps and advanced backend processing, as well as activity recommendations based on weather conditions.


## Stack
- **Frontend:** React (Vite), TypeScript, Leaflet, MUI, Recharts
- **Backend:** FastAPI (async Python), SQLAlchemy, GeoAlchemy2
- **Database:** PostgreSQL + PostGIS
- **Cache:** Redis
- **Jobs:** Celery + Celery Beat (RabbitMQ broker)
- **Other:** Docker, Alembic (migrations), pandas

## Features

### Interactive Map & Data

### Backend API

- Endpoints for:
  - Current and hourly air quality, weather, and comarques lookup
  - Materialized view and caching for fast comarques GeoJSON
  - Async data fetching, pandas DataFrame processing, robust schema alignment
- Celery periodic tasks for data refresh, and caching

### Celery Periodic Tasks

- Refresh radar timestamps
- Refresh alerts
- Cache comarca forecasts (hourly)
- Schedules adjustable in `backend/app/workers/celery_app.py`


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

### Episodis Oberts (Warnings)
- `GET /api/v1/meteocat/episodis-oberts` — List of current warnings, with affected comarques and periods.

## Frontend Features

- `/` — Main dashboard with activity recommendations.
- Historical Data: View past weather data by date.
- Air Quality Map: Select parameter, see colormap, hover for tooltip, click for hourly modal.
- Meteo Alerts: See warnings by period, colored overlays, and tooltips.
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

## Development Notes

- All code is type-checked and linted
- Main map logic: [frontend/src/components/AirQualityMap.tsx](frontend/src/components/AirQualityMap.tsx), [frontend/src/components/EpisodisOberts.tsx](frontend/src/components/EpisodisOberts.tsx)
- All API routes: [backend/app/api/v1/endpoints/](backend/app/api/v1/endpoints/)
- Air quality data logic: [backend/app/services/air_quality/service.py](backend/app/services/air_quality/service.py)
- Celery/worker logic: [backend/app/workers/](backend/app/workers/)
- Database models: [backend/app/db/models/](backend/app/db/models/)
- Alembic migrations: [backend/alembic/versions/](backend/alembic/versions/)

---

## Project Structure

- `frontend/` — React app (Vite, TypeScript)
- `backend/` — FastAPI app, DB models, services, workers
- `docker/` — Docker, Nginx, DB init scripts
- `models/` — ML models (e.g., recommender.joblib)
- `data/` — Sample data (e.g., comarcas_sample.geojson)
- `scripts/` — Utility scripts (e.g., load_comarcas.py)

---

## License

MIT License