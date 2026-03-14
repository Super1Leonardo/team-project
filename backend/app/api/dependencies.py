from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.infra.db.session import DatabaseManager
from app.infra.gateways.collector_gateway import CollectorGateway
from app.infra.gateways.health_gateway import ExternalHealthGateway
from app.infra.gateways.ml_gateway import MLGateway
from app.infra.gateways.notifier_gateway import NotifierGateway
from app.infra.health.registry import HealthRegistry
from app.infra.redis.client import RedisClient, build_redis_client
from app.modules.alerts.repository import AlertRepository
from app.modules.alerts.service import AlertService
from app.modules.analytics.repository import AnalyticsRepository
from app.modules.analytics.service import AnalyticsService
from app.modules.brands.repository import BrandRepository
from app.modules.brands.service import BrandService
from app.modules.collector.service import CollectorService
from app.modules.events.repository import EventLogRepository
from app.modules.events.service import EventLogService
from app.modules.health.service import HealthService
from app.modules.mentions.repository import MentionRepository
from app.modules.mentions.services.brand_match import BrandMatchService
from app.modules.mentions.services.dedup import DeduplicationService
from app.modules.mentions.services.ingest import MentionIngestService
from app.modules.mentions.services.query import MentionQueryService
from app.modules.projects.repository import ProjectRepository
from app.modules.projects.service import ProjectService
from app.modules.sources.repository import SourceRepository
from app.modules.sources.service import SourceService
from app.modules.statuses.repository import ComponentStatusRepository
from app.modules.statuses.service import StatusesService


@dataclass
class AppContainer:
    settings: Settings
    database_manager: DatabaseManager
    redis_client: RedisClient

    project_service: ProjectService
    brand_service: BrandService
    source_service: SourceService
    collector_service: CollectorService
    mention_ingest_service: MentionIngestService
    mention_query_service: MentionQueryService
    analytics_service: AnalyticsService
    alert_service: AlertService
    event_log_service: EventLogService
    health_service: HealthService
    statuses_service: StatusesService

    async def shutdown(self) -> None:
        await self.database_manager.dispose()
        await self.redis_client.close()


def build_container(settings: Settings | None = None) -> AppContainer:
    resolved_settings = settings or get_settings()

    database_manager = DatabaseManager(resolved_settings)
    redis_client = build_redis_client(resolved_settings)

    project_repository = ProjectRepository(database_manager)
    brand_repository = BrandRepository(database_manager)
    source_repository = SourceRepository(database_manager)
    mention_repository = MentionRepository(database_manager)
    alert_repository = AlertRepository(database_manager)
    event_repository = EventLogRepository(database_manager)
    analytics_repository = AnalyticsRepository(database_manager)
    status_repository = ComponentStatusRepository(database_manager)

    event_log_service = EventLogService(event_repository)
    project_service = ProjectService(project_repository, event_log_service)
    brand_service = BrandService(brand_repository, project_repository, event_log_service)
    source_service = SourceService(source_repository, project_repository, event_log_service)

    health_gateway = ExternalHealthGateway(resolved_settings.request_timeout_seconds)
    collector_gateway = CollectorGateway(resolved_settings, health_gateway)
    ml_gateway = MLGateway(resolved_settings, health_gateway)
    notifier_gateway = NotifierGateway(resolved_settings, health_gateway)

    alert_service = AlertService(
        repository=alert_repository,
        brand_repository=brand_repository,
        redis_client=redis_client,
        notifier=notifier_gateway,
        event_log_service=event_log_service,
    )
    collector_service = CollectorService(source_repository, collector_gateway, event_log_service)

    brand_match_service = BrandMatchService()
    deduplication_service = DeduplicationService(mention_repository)
    mention_ingest_service = MentionIngestService(
        source_repository=source_repository,
        brand_repository=brand_repository,
        mention_repository=mention_repository,
        event_log_service=event_log_service,
        brand_match_service=brand_match_service,
        deduplication_service=deduplication_service,
        ml_gateway=ml_gateway,
        alert_service=alert_service,
    )
    mention_query_service = MentionQueryService(
        mention_repository=mention_repository,
        source_repository=source_repository,
        brand_repository=brand_repository,
    )

    analytics_service = AnalyticsService(analytics_repository)
    health_registry = HealthRegistry(database_manager, redis_client, ml_gateway, collector_gateway)
    health_service = HealthService(health_registry, status_repository, event_log_service)
    statuses_service = StatusesService(status_repository, health_service)

    return AppContainer(
        settings=resolved_settings,
        database_manager=database_manager,
        redis_client=redis_client,
        project_service=project_service,
        brand_service=brand_service,
        source_service=source_service,
        collector_service=collector_service,
        mention_ingest_service=mention_ingest_service,
        mention_query_service=mention_query_service,
        analytics_service=analytics_service,
        alert_service=alert_service,
        event_log_service=event_log_service,
        health_service=health_service,
        statuses_service=statuses_service,
    )


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


def get_project_service(container: AppContainer = Depends(get_container)) -> ProjectService:
    return container.project_service


def get_brand_service(container: AppContainer = Depends(get_container)) -> BrandService:
    return container.brand_service


def get_source_service(container: AppContainer = Depends(get_container)) -> SourceService:
    return container.source_service


def get_collector_service(container: AppContainer = Depends(get_container)) -> CollectorService:
    return container.collector_service


def get_mention_ingest_service(container: AppContainer = Depends(get_container)) -> MentionIngestService:
    return container.mention_ingest_service


def get_mention_query_service(container: AppContainer = Depends(get_container)) -> MentionQueryService:
    return container.mention_query_service


def get_analytics_service(container: AppContainer = Depends(get_container)) -> AnalyticsService:
    return container.analytics_service


def get_alert_service(container: AppContainer = Depends(get_container)) -> AlertService:
    return container.alert_service


def get_event_log_service(container: AppContainer = Depends(get_container)) -> EventLogService:
    return container.event_log_service


def get_health_service(container: AppContainer = Depends(get_container)) -> HealthService:
    return container.health_service


def get_statuses_service(container: AppContainer = Depends(get_container)) -> StatusesService:
    return container.statuses_service
