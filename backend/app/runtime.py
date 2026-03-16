from __future__ import annotations

from dataclasses import dataclass

from backend.app.collectors.rss import RssCollector
from backend.app.collectors.telegram import TelegramCollector
from backend.app.collectors.website import WebsiteCollector
from backend.app.core.config import Settings
from backend.app.infra.db.clickhouse import ClickHouseMentionEventsStore
from backend.app.infra.db.postgres import BrandRadarPostgresStore
from backend.app.infra.gateways.telegram_gateway import TelegramGateway
from backend.app.ml.ml_gateway import ExternalMLGateway
from backend.app.ml.normalizer import MLResultNormalizer
from backend.app.workers.collector_worker import CollectorWorker
from backend.app.workers.ml_worker import MLWorker


@dataclass(slots=True)
class ArchitectureRuntime:
    postgres_store: BrandRadarPostgresStore
    clickhouse_store: ClickHouseMentionEventsStore
    telegram_gateway: TelegramGateway
    external_ml_gateway: ExternalMLGateway
    collector_worker: CollectorWorker
    ml_normalizer: MLResultNormalizer
    ml_worker: MLWorker


def build_runtime(settings: Settings) -> ArchitectureRuntime:
    postgres_store = BrandRadarPostgresStore(settings)
    clickhouse_store = ClickHouseMentionEventsStore(settings)
    telegram_gateway = TelegramGateway(settings)
    external_ml_gateway = ExternalMLGateway(settings)
    telegram_collector = TelegramCollector(telegram_gateway)
    rss_collector = RssCollector()
    website_collector = WebsiteCollector()
    collector_worker = CollectorWorker(
        postgres_store,
        collectors={
            "telegram": telegram_collector,
            "rss": rss_collector,
            "website": website_collector,
        },
        lookback_days=settings.collector_lookback_days,
        idle_sleep_seconds=settings.collector_idle_sleep_seconds,
    )
    ml_normalizer = MLResultNormalizer(
        postgres_store,
        dedup_threshold=settings.ml_dedup_threshold,
    )
    ml_worker = MLWorker(
        store=postgres_store,
        clickhouse_store=clickhouse_store,
        gateway=external_ml_gateway,
        normalizer=ml_normalizer,
        batch_size=settings.ml_worker_batch_size,
        idle_sleep_seconds=settings.ml_worker_idle_sleep_seconds,
    )
    return ArchitectureRuntime(
        postgres_store=postgres_store,
        clickhouse_store=clickhouse_store,
        telegram_gateway=telegram_gateway,
        external_ml_gateway=external_ml_gateway,
        collector_worker=collector_worker,
        ml_normalizer=ml_normalizer,
        ml_worker=ml_worker,
    )
