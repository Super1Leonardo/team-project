from functools import lru_cache

from backend.app.core.config import Settings, get_settings
from backend.app.infra.db.clickhouse import ClickHouseMentionEventsStore
from backend.app.infra.db.postgres import BrandRadarPostgresStore
from backend.app.modules.brandradar.service import BrandRadarService
from backend.app.runtime import ArchitectureRuntime, build_runtime


@lru_cache
def get_app_settings() -> Settings:
    return get_settings()


@lru_cache
def get_brandradar_postgres_store() -> BrandRadarPostgresStore:
    return BrandRadarPostgresStore(get_app_settings())


@lru_cache
def get_brandradar_clickhouse_store() -> ClickHouseMentionEventsStore:
    return ClickHouseMentionEventsStore(get_app_settings())


@lru_cache
def get_brandradar_runtime() -> ArchitectureRuntime:
    return build_runtime(get_app_settings())


@lru_cache
def get_brandradar_service() -> BrandRadarService:
    return BrandRadarService(get_brandradar_runtime())
