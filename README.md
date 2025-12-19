# Catalunya Weather (React + FastAPI + Redis + PostGIS + Celery/RabbitMQ)

Monorepo skeleton for a Catalunya-focused weather web app that can start as a hobby project and evolve into a production-grade architecture.

## Stack
- **Frontend:** React (Vite) + MapLibre GL
- **Backend:** FastAPI (Python)
- **Cache:** Redis
- **DB:** Postgres + PostGIS (SQLAlchemy async + GeoAlchemy2)
- **Jobs:** Celery worker + Celery Beat (broker: RabbitMQ)

## Philosophy
Expose a **stable internal API** (your FastAPI routes), and blend providers behind the scenes:
- Point forecasts: **Open-Meteo** (implemented)
- Catalunya comarca daily forecasts: **Meteocat** (implemented with sample payload; plug real endpoint later)
- Alerts: placeholder (CAP feed)
- Radar: **RainViewer** proxied tiles (implemented)
- Air quality: placeholder (Generalitat XVPCA)

## Quickstart
```bash
cp .env.example .env
docker compose up --build
```

Backend:
- Health: http://localhost:8000/api/health
- Docs: http://localhost:8000/api/docs

Frontend:
- http://localhost:5173

RabbitMQ management UI:
- http://localhost:15672 (guest/guest)

## Database migration + sample comarca load
```bash
docker compose exec api alembic upgrade head
docker compose exec api python scripts/load_comarcas.py
```

The sample GeoJSON includes 3 simplified comarcas so you can validate the whole flow:
- Map click -> point forecast (Open-Meteo)
- Map click -> PostGIS lookup -> comarca forecast (Meteocat sample payload)

## Key endpoints
- `GET /api/v1/forecast?lat=..&lon=..&tz=Europe/Madrid`
- `GET /api/v1/comarcas/lookup?lat=..&lon=..`
- `GET /api/v1/forecast/comarca/lookup?lat=..&lon=..`

Radar:
- `GET /api/v1/radar/timestamps`
- `GET /api/v1/radar/tiles/{timestamp}/{z}/{x}/{y}.png`

Notifications:
- `POST /api/v1/users`
- `POST /api/v1/rules`
- `GET /api/v1/events`

## Celery periodic tasks
Celery Beat runs:
- refresh radar timestamps
- refresh alerts (placeholder)
- cache comarca forecasts (hourly)
- evaluate notification rules (every 5 minutes)

You can adjust schedules in `backend/app/workers/celery_app.py`.

## Plugging real Meteocat comarca forecasts
Keep `METEOCAT_USE_SAMPLE=1` until you know the exact OpenData endpoint and payload format.
When ready:
- set `METEOCAT_USE_SAMPLE=0`
- set `METEOCAT_COMARCA_FORECAST_URL_TEMPLATE=...{code}...`
- adapt `backend/app/services/providers/meteocat.py` parsing if needed.
