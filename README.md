# Catalunya Weather (React + FastAPI + Redis + PostGIS + Celery/RabbitMQ)

Monorepo skeleton for a Catalunya-focused weather web app that can start as a hobby project and evolve into a production-grade architecture.

## Stack
- **Frontend:** React (Vite) + Leaflet + TailwindCSS
- **Backend:** FastAPI (Python)
- **Cache:** Redis
- **DB:** Postgres + PostGIS (SQLAlchemy async + GeoAlchemy2)
- **Jobs:** Celery worker + Celery Beat (broker: RabbitMQ)

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
- http://localhost:15672 (guest/guest)

## Database migration + sample comarca load
```bash
docker compose exec api alembic upgrade head
docker compose exec api python scripts/load_comarcas.py
```

The sample GeoJSON includes the 42 comarcas of Catalunya (Spain).

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
- refresh alerts
- cache comarca forecasts (hourly)
- evaluate notification rules (every 5 minutes)

The schedules can be adjusted in `backend/app/workers/celery_app.py`.

