from __future__ import annotations

import asyncio
from typing import Any

from backend.app.collectors.base import BaseCollector
from backend.app.infra.db.postgres import BrandRadarPostgresStore


class CollectorWorker:
    def __init__(
        self,
        store: BrandRadarPostgresStore,
        collectors: dict[str, BaseCollector],
        *,
        per_source_limit: int = 100,
        idle_sleep_seconds: float = 30.0,
    ):
        self.store = store
        self.collectors = collectors
        self.per_source_limit = per_source_limit
        self.idle_sleep_seconds = idle_sleep_seconds

    async def run_once(self) -> dict[str, Any]:
        due_sources = await asyncio.to_thread(self.store.list_due_sources)
        return await self.run_sources(due_sources)

    async def run_sources(
        self,
        sources: list[dict[str, Any]],
        *,
        per_source_limit: int | None = None,
    ) -> dict[str, Any]:
        summary = {
            "sources_checked": len(sources),
            "sources_processed": 0,
            "posts_saved": 0,
            "errors": [],
        }
        limit = per_source_limit if per_source_limit is not None else self.per_source_limit

        for source in sources:
            collector = self.collectors.get(source["source_type"])
            if collector is None:
                error = f"Collector for source_type '{source['source_type']}' is not implemented."
                await asyncio.to_thread(self.store.record_collection_error, source, error)
                summary["errors"].append({"source_id": source["id"], "error": error})
                continue

            try:
                posts = await collector.collect(source, limit=limit)
                saved_count = await asyncio.to_thread(self.store.save_raw_posts, source, posts)
                summary["sources_processed"] += 1
                summary["posts_saved"] += saved_count
            except Exception as exc:
                await asyncio.to_thread(self.store.record_collection_error, source, str(exc))
                summary["errors"].append({"source_id": source["id"], "error": str(exc)})

        return summary

    async def run_forever(self, stop_event: asyncio.Event | None = None) -> None:
        event = stop_event or asyncio.Event()

        while not event.is_set():
            await self.run_once()
            try:
                await asyncio.wait_for(event.wait(), timeout=self.idle_sleep_seconds)
            except TimeoutError:
                continue
