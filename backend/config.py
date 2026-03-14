from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    telegram_phone: str | None = None
    telegram_session_path: Path = Path("backend/data/telegram_parser")
    api_title: str = "Telegram Parser API"
    api_version: str = "0.1.0"
    backend_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    public_backend_api_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def credentials_configured(self) -> bool:
        return bool(self.telegram_api_id and self.telegram_api_hash)

    @property
    def cors_origins(self) -> list[str]:
        return [
            item.strip()
            for item in self.backend_cors_origins.split(",")
            if item.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.telegram_session_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
