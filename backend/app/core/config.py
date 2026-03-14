from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Brand Radar Backend"
    app_version: str = "0.1.0"
    environment: str = "local"

    database_url: str | None = None
    redis_url: str | None = None
    ml_service_url: str | None = None
    collector_service_url: str | None = None
    notifier_webhook_url: str | None = None

    request_timeout_seconds: float = 3.0
    default_limit: int = 20
    max_limit: int = 100

    demo_mode: bool = True
    ml_health_path: str = "/health"
    collector_health_path: str = "/health"

    model_config = SettingsConfigDict(
        env_prefix="BRANDRADAR_",
        extra="ignore",
    )

    @property
    def use_in_memory_store(self) -> bool:
        return not self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
