from __future__ import annotations

from dataclasses import dataclass

from backend.app.collectors.telegram import TelegramCollector
from backend.app.core.config import Settings
from backend.app.infra.db.clickhouse import ClickHouseMentionEventsStore
from backend.app.infra.db.postgres import BrandRadarPostgresStore
from backend.app.infra.gateways.ml_gateway import ExternalMLGateway
from backend.app.infra.gateways.telegram_gateway import TelegramGateway
from backend.app.ml.dedup import PgVectorDeduplicator
from backend.app.ml.pipeline import MLPipeline
from backend.app.workers.collector_worker import CollectorWorker
from backend.app.workers.ml_worker import MLWorker


@dataclass(slots=True)
class ArchitectureRuntime:
    postgres_store: BrandRadarPostgresStore
    clickhouse_store: ClickHouseMentionEventsStore
    telegram_gateway: TelegramGateway
    external_ml_gateway: ExternalMLGateway
    collector_worker: CollectorWorker
    ml_pipeline: MLPipeline
    ml_worker: MLWorker


def build_runtime(settings: Settings) -> ArchitectureRuntime:
    postgres_store = BrandRadarPostgresStore(settings)
    clickhouse_store = ClickHouseMentionEventsStore(settings)
    telegram_gateway = TelegramGateway(settings)
    external_ml_gateway = ExternalMLGateway(settings)
    telegram_collector = TelegramCollector(telegram_gateway)
    collector_worker = CollectorWorker(
        postgres_store,
        collectors={"telegram": telegram_collector},
        per_source_limit=settings.collector_per_source_limit,
        idle_sleep_seconds=settings.collector_idle_sleep_seconds,
    )
    ml_pipeline = MLPipeline(
        store=postgres_store,
        clickhouse_store=clickhouse_store,
        deduplicator=PgVectorDeduplicator(
            postgres_store,
            threshold=settings.ml_dedup_threshold,
        ),
    )
    ml_worker = MLWorker(
        ml_pipeline,
        batch_size=settings.ml_worker_batch_size,
        idle_sleep_seconds=settings.ml_worker_idle_sleep_seconds,
    )
    return ArchitectureRuntime(
        postgres_store=postgres_store,
        clickhouse_store=clickhouse_store,
        telegram_gateway=telegram_gateway,
        external_ml_gateway=external_ml_gateway,
        collector_worker=collector_worker,
        ml_pipeline=ml_pipeline,
        ml_worker=ml_worker,
    )
