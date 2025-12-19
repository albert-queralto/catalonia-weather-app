from __future__ import annotations

from typing import List

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration.

    Uses environment variables (and .env in local/dev). Keep secrets out of git.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = Field(default="Catalunya Weather", alias="PROJECT_NAME")
    environment: str = Field(default="dev", alias="ENVIRONMENT")

    api_base_path: str = Field(default="/api", alias="API_BASE_PATH")
    cors_origins: str = Field(default="", alias="CORS_ORIGINS")

    database_url: str = Field(
        default="postgresql+asyncpg://weather:weather@postgres:5432/weather", alias="DATABASE_URL"
    )

    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    celery_result_backend: str = Field(default="redis://redis:6379/1", alias="CELERY_RESULT_BACKEND")
    celery_broker_url: str = Field(default="amqp://guest:guest@rabbitmq:5672//", alias="CELERY_BROKER_URL")

    meteocat_pronostic_base_url: str = "https://api.meteo.cat/pronostic/v1"
    meteocat_use_sample: str = Field(default="1", alias="METEOCAT_USE_SAMPLE")
    meteocat_comarca_forecast_url_template: str = Field(default="", alias="METEOCAT_COMARCA_FORECAST_URL_TEMPLATE")
    meteocat_xema_base_url: str = Field(
        default="https://api.meteo.cat/xema/v1", alias="METEOCAT_XEMA_BASE_URL"
    )

    meteocat_api_key: str = Field(default="", alias="METEOCAT_API_KEY")
    aemet_api_key: str = Field(default="", alias="AEMET_API_KEY")
    weatherkit_token: str = Field(default="", alias="WEATHERKIT_TOKEN")

    @property
    def cors_origin_list(self) -> List[str]:
        if not self.cors_origins:
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
