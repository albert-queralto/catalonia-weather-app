from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.services.cache import cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await cache.connect()
    try:
        yield
    finally:
        # Shutdown
        await cache.close()


app = FastAPI(title=settings.project_name, lifespan=lifespan)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.api_base_path)
