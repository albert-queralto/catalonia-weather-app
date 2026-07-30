# Catalunya Weather (React + FastAPI + Redis + PostGIS + Celery/RabbitMQ)

A full-stack web application focused on Catalonia, providing real-time weather, air quality, warning data with interactive maps and advanced backend processing, as well as activity recommendations based on weather conditions.

---

## Stack
- **Frontend:** React (Vite), TypeScript, Leaflet, MUI, Recharts
- **Backend:** FastAPI (async Python), SQLAlchemy, GeoAlchemy2
- **Database:** PostgreSQL + PostGIS
- **Cache:** Redis
- **Jobs:** Celery + Celery Beat (RabbitMQ broker)
- **Other:** Docker, Alembic (migrations), pandas

---

## Features

### User Experience
- Responsive UI with MUI and Recharts
- Interactive maps for weather, air quality, and warnings
- User authentication (JWT-based), registration, and role-based access
- Activity recommendations based on weather and user preferences
- Historical data visualization
- Air quality and weather alerts
- User profile and preferences (planned)
- Dark mode (planned)
- PWA/offline support (planned)

### Backend API
- Endpoints for:
  - Current and hourly air quality, weather, and comarques lookup
  - Materialized view and caching for fast comarques GeoJSON
  - Async data fetching, pandas DataFrame processing, robust schema alignment
- Celery periodic tasks for data refresh, and caching
- Role-based access and admin endpoints
- JWT authentication with configurable expiration
- Audit logging and error handling (planned)
- Email verification and password reset (planned)

### Celery Periodic Tasks
- Refresh radar timestamps
- Refresh alerts
- Cache comarca forecasts (hourly)
- Update Meteocat station measurements daily for the latest completed Catalonia day
- Schedules adjustable in `backend/app/workers/celery_app.py`

---

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

---

## Database migration + sample comarca load
```bash
docker compose exec api alembic upgrade head
docker compose exec api python scripts/load_comarcas.py
```
The sample GeoJSON includes the 42 comarques of Catalonia (Spain).

---

## Key Endpoints

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

### Auth & Users
- `POST /api/v1/auth/register` — Register a new user
- `POST /api/v1/auth/token` — Obtain JWT token
- `GET /api/v1/auth/me` — Get current user info

---

## Frontend Features

- `/` — Main dashboard with activity recommendations.
- `/login` — User login
- `/register` — User registration
- `/historical` — View past weather data by date.
- `/air-quality-map` — Select parameter, see colormap, hover for tooltip, click for hourly modal.
- `/episodis-oberts` — See warnings by period, colored overlays, and tooltips.
- `/suggest-activity` — Suggest activities based on weather
- `/activities` — List all activities
- `/manage-categories` — Admin: manage activity categories

---

## Backend Features

- FastAPI async endpoints, robust error handling, and schema validation.
- Materialized view for comarcas (EPSG:4326) for fast spatial queries.
- Redis caching for GeoJSON and other heavy endpoints.
- Data ingestion and transformation with pandas.
- Celery tasks for periodic data refresh and notification rule evaluation.
- Role-based access and admin endpoints.
- JWT authentication and user management.

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

## Roadmap / Planned Improvements

- User profile and preferences
- Dark mode and accessibility improvements
- PWA/offline support
- Email verification and password reset
- Push notifications for alerts
- Data export (CSV/JSON)
- Feedback loop for ML recommendations
- CI/CD and test coverage improvements

---

## License

MIT License
