from functools import lru_cache

from backend.app.core.config import Settings, get_settings
from backend.app.infra.db.clickhouse import ClickHouseMentionEventsStore
from backend.app.infra.db.postgres import BrandRadarPostgresStore
from backend.app.infra.gateways.telegram_gateway import TelegramGateway
from backend.app.modules.brandradar.service import BrandRadarService
from backend.app.modules.collector.service import CollectorService
from backend.app.modules.health.service import HealthService
from backend.app.modules.ml.repository import MLResultsRepository
from backend.app.modules.ml.service import MLService
from backend.app.modules.messages.repository import MessagesRepository
from backend.app.modules.messages.service import MessagesService
from backend.app.modules.sources.repository import ParserSettingsRepository
from backend.app.modules.sources.service import SourcesService
from backend.app.runtime import ArchitectureRuntime, build_runtime


@lru_cache
def get_app_settings() -> Settings:
    return get_settings()


@lru_cache
def get_sources_repository() -> ParserSettingsRepository:
    return ParserSettingsRepository(get_app_settings())


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
def get_messages_repository() -> MessagesRepository:
    return MessagesRepository(get_app_settings())


@lru_cache
def get_ml_results_repository() -> MLResultsRepository:
    return MLResultsRepository(get_app_settings())


@lru_cache
def get_telegram_gateway() -> TelegramGateway:
    return TelegramGateway(get_app_settings())


@lru_cache
def get_sources_service() -> SourcesService:
    return SourcesService(get_sources_repository(), get_app_settings())


@lru_cache
def get_messages_service() -> MessagesService:
    return MessagesService(get_messages_repository())


@lru_cache
def get_ml_service() -> MLService:
    return MLService(get_ml_results_repository())


@lru_cache
def get_collector_service() -> CollectorService:
    return CollectorService(
        get_telegram_gateway(),
        get_sources_repository(),
        get_messages_repository(),
    )


@lru_cache
def get_brandradar_service() -> BrandRadarService:
    return BrandRadarService(get_brandradar_runtime())


@lru_cache
def get_health_service() -> HealthService:
    return HealthService()
