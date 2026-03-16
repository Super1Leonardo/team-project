from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.app.collectors.base import BaseCollector
from backend.app.infra.db.postgres import BrandRadarPostgresStore

logger = logging.getLogger(__name__)


class CollectorWorker:
    def __init__(
        self,
        store: BrandRadarPostgresStore,
        collectors: dict[str, BaseCollector],
        *,
        lookback_days: int = 30,
        source_concurrency: int = 4,
        idle_sleep_seconds: float = 30.0,
    ):
        self.store = store
        self.collectors = collectors
        self.lookback_days = lookback_days
        self.source_concurrency = max(1, source_concurrency)
        self.idle_sleep_seconds = idle_sleep_seconds

    async def run_once(self) -> dict[str, Any]:
        due_sources = await asyncio.to_thread(self.store.list_due_sources)
        return await self.run_sources(due_sources)

    async def run_sources(
        self,
        sources: list[dict[str, Any]],
        *,
        lookback_days: int | None = None,
    ) -> dict[str, Any]:
        summary = {
            "sources_checked": len(sources),
            "sources_processed": 0,
            "posts_saved": 0,
            "errors": [],
        }
        effective_lookback_days = (
            lookback_days if lookback_days is not None else self.lookback_days
        )
        published_after = datetime.now(UTC) - timedelta(days=effective_lookback_days)
        semaphore = asyncio.Semaphore(self.source_concurrency)

        async def process_source(source: dict[str, Any]) -> dict[str, Any]:
            collector = self.collectors.get(source["source_type"])
            if collector is None:
                error = f"Collector for source_type '{source['source_type']}' is not implemented."
                await asyncio.to_thread(self.store.record_collection_error, source, error)
                return {
                    "sources_processed": 0,
                    "posts_saved": 0,
                    "error": {"source_id": source["id"], "error": error},
                }

            async with semaphore:
                try:
                    posts = await collector.collect(
                        source,
                        published_after=published_after,
                    )
                    saved_count = await asyncio.to_thread(self.store.save_raw_posts, source, posts)
                    return {
                        "sources_processed": 1,
                        "posts_saved": saved_count,
                        "error": None,
                    }
                except Exception as exc:
                    await asyncio.to_thread(self.store.record_collection_error, source, str(exc))
                    return {
                        "sources_processed": 0,
                        "posts_saved": 0,
                        "error": {"source_id": source["id"], "error": str(exc)},
                    }

        results = await asyncio.gather(*(process_source(source) for source in sources))

        for result in results:
            summary["sources_processed"] += int(result["sources_processed"])
            summary["posts_saved"] += int(result["posts_saved"])
            if result["error"] is not None:
                summary["errors"].append(result["error"])

        return summary

    async def run_forever(self, stop_event: asyncio.Event | None = None) -> None:
        event = stop_event or asyncio.Event()

        while not event.is_set():
            try:
                await self.run_once()
            except Exception:
                logger.exception("Collector worker iteration failed.")
            try:
                await asyncio.wait_for(event.wait(), timeout=self.idle_sleep_seconds)
            except TimeoutError:
                continue
