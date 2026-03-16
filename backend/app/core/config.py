from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    parser_db_host: str = "localhost"
    parser_db_port: int = 5432
    parser_db_name: str = "brandradar"
    parser_db_user: str = "brandradar"
    parser_db_password: str = "brandradar"
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_database: str = "brandradar_ml"
    clickhouse_user: str = "brandradar"
    clickhouse_password: str = "brandradar"
    external_ml_base_url: str = "http://178.154.216.255:8000"
    external_ml_predict_path: str = "/analyze_batch"
    external_ml_health_path: str = "/health"
    external_ml_timeout_seconds: float = 60.0
    external_ml_connect_timeout_seconds: float = 3.0
    external_ml_health_timeout_seconds: float = 2.0
    collector_lookback_days: int = 30
    collector_source_concurrency: int = 4
    collector_idle_sleep_seconds: float = 5.0
    ml_worker_batch_size: int = 100
    ml_worker_idle_sleep_seconds: float = 2.0
    ml_dedup_threshold: float = 0.15
    ml_cluster_threshold: float = 0.22
    backend_metrics_window_seconds: int = 60
    backend_metrics_log_interval_seconds: float = 10.0
    backend_slow_request_threshold_ms: float = 1_000.0
    api_title: str = "BrandRadar API"
    api_version: str = "0.1.0"
    backend_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        return [
            item.strip()
            for item in self.backend_cors_origins.split(",")
            if item.strip()
        ]

    @property
    def parser_database_url(self) -> str:
        user = quote_plus(self.parser_db_user)
        password = quote_plus(self.parser_db_password)
        return (
            f"postgresql://{user}:{password}@{self.parser_db_host}:"
            f"{self.parser_db_port}/{self.parser_db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
