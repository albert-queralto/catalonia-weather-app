from fastapi import APIRouter

from app.api.v1.endpoints import (
    air_quality,
    alerts,
    comarcas,
    health,
    meteocat,
    forecast,
    auth,
    recommender,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/v1", tags=["auth"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(comarcas.router, prefix="/v1", tags=["geo"])
api_router.include_router(alerts.router, prefix="/v1", tags=["alerts"])
api_router.include_router(air_quality.router, prefix="/v1", tags=["air_quality"])
api_router.include_router(meteocat.router, prefix="/v1", tags=["meteocat"])
api_router.include_router(forecast.router, prefix="/v1", tags=["forecast"])
api_router.include_router(recommender.router, prefix="/v1", tags=["recommender"])