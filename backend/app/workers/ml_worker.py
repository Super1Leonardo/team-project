from __future__ import annotations

import asyncio
import logging
from typing import Any

from backend.app.infra.db.clickhouse import ClickHouseMentionEventsStore
from backend.app.infra.db.postgres import BrandRadarPostgresStore
from backend.app.ml.ml_gateway import ExternalMLGateway
from backend.app.ml.normalizer import MLResultNormalizer

logger = logging.getLogger(__name__)


class MLWorker:
    def __init__(
        self,
        *,
        store: BrandRadarPostgresStore,
        clickhouse_store: ClickHouseMentionEventsStore,
        gateway: ExternalMLGateway,
        normalizer: MLResultNormalizer,
        batch_size: int = 100,
        idle_sleep_seconds: float = 15.0,
    ):
        self.store = store
        self.clickhouse_store = clickhouse_store
        self.gateway = gateway
        self.normalizer = normalizer
        self.batch_size = batch_size
        self.idle_sleep_seconds = idle_sleep_seconds

    async def run_once(self, batch_size: int | None = None) -> dict[str, Any]:
        effective_batch_size = batch_size if batch_size is not None else self.batch_size
        raw_posts = await asyncio.to_thread(
            self.store.fetch_unprocessed_raw_posts,
            effective_batch_size,
        )
        queue_items = self.normalizer.build_queue_items(raw_posts)
        if not queue_items:
            return {
                "batch_size": 0,
                "stored_count": 0,
                "synced_count": 0,
                "projects": {},
            }

        remote_response = await self.gateway.predict(queue_items)
        remote_results = self.normalizer.extract_remote_results(remote_response)
        mention_rows = await asyncio.to_thread(
            self.normalizer.normalize_remote_results,
            queue_items=queue_items,
            remote_results=remote_results,
        )
        result = await asyncio.to_thread(
            self.store.persist_mentions,
            mention_rows,
            self.clickhouse_store.insert_mention_events,
        )
        return {
            "batch_size": len(queue_items),
            "stored_count": result["stored_count"],
            "synced_count": result["synced_count"],
            "projects": result["projects"],
        }

    async def run_forever(self, stop_event: asyncio.Event | None = None) -> None:
        event = stop_event or asyncio.Event()

        while not event.is_set():
            try:
                await self.run_once()
            except Exception:
                logger.exception("ML worker iteration failed.")
            try:
                await asyncio.wait_for(event.wait(), timeout=self.idle_sleep_seconds)
            except TimeoutError:
                continue
