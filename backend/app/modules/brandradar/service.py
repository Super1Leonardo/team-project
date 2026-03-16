from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from backend.app.core.exceptions import ResourceNotFoundError
from backend.app.runtime import ArchitectureRuntime

logger = logging.getLogger(__name__)


class BrandRadarService:
    def __init__(self, runtime: ArchitectureRuntime):
        self.runtime = runtime

    async def list_projects(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self.runtime.postgres_store.list_projects)

    async def get_project(self, project_id: int) -> dict[str, Any]:
        return await asyncio.to_thread(self.runtime.postgres_store.get_project, project_id)

    async def create_project(self, payload) -> dict[str, Any]:
        return await asyncio.to_thread(
            self.runtime.postgres_store.create_project,
            name=payload.name,
            keywords=payload.keywords,
            exclude_keywords=payload.exclude_keywords,
            risk_words=payload.risk_words,
        )

    async def update_project(self, project_id: int, payload) -> dict[str, Any]:
        existing_project = await asyncio.to_thread(
            self.runtime.postgres_store.get_project,
            project_id,
        )
        updated_project = await asyncio.to_thread(
            self.runtime.postgres_store.update_project,
            project_id,
            name=payload.name,
            keywords=payload.keywords,
            exclude_keywords=payload.exclude_keywords,
            risk_words=payload.risk_words,
        )
        requires_feed_refresh = any(
            existing_project[key] != updated_project[key]
            for key in ("keywords", "exclude_keywords", "risk_words")
        )
        if not requires_feed_refresh:
            return updated_project

        await asyncio.to_thread(
            self.runtime.postgres_store.reset_project_mentions_for_reprocessing,
            project_id,
        )
        try:
            await self.runtime.ml_worker.run_until_project_queue_drained(project_id)
        except Exception:
            logger.exception(
                "Project %s was updated, mentions were requeued, but immediate reprocessing failed.",
                project_id,
            )

        return await asyncio.to_thread(
            self.runtime.postgres_store.get_project,
            project_id,
        )

    async def delete_project(self, project_id: int) -> None:
        await asyncio.to_thread(self.runtime.postgres_store.delete_project, project_id)

    async def list_sources(self, project_id: int) -> list[dict[str, Any]]:
        await asyncio.to_thread(self.runtime.postgres_store.get_project, project_id)
        return await asyncio.to_thread(
            self.runtime.postgres_store.list_sources,
            project_id=project_id,
        )

    async def get_source(self, project_id: int, source_id: int) -> dict[str, Any]:
        return await asyncio.to_thread(
            self.runtime.postgres_store.get_source,
            project_id,
            source_id,
        )

    async def create_source(self, project_id: int, payload) -> dict[str, Any]:
        return await asyncio.to_thread(
            self.runtime.postgres_store.create_source,
            project_id=project_id,
            source_type=payload.source_type,
            source_config=payload.source_config,
            is_active=payload.is_active,
            poll_interval_s=payload.poll_interval_s,
        )

    async def update_source(self, project_id: int, source_id: int, payload) -> dict[str, Any]:
        return await asyncio.to_thread(
            self.runtime.postgres_store.update_source,
            project_id,
            source_id,
            source_type=payload.source_type,
            source_config=payload.source_config,
            is_active=payload.is_active,
            poll_interval_s=payload.poll_interval_s,
        )

    async def delete_source(self, project_id: int, source_id: int) -> None:
        await asyncio.to_thread(
            self.runtime.postgres_store.delete_source,
            project_id,
            source_id,
        )

    async def trigger_collector_run(
        self,
        *,
        project_id: int,
        source_ids: list[int] | None = None,
        limit_per_source: int | None = None,
    ) -> dict[str, Any]:
        await asyncio.to_thread(self.runtime.postgres_store.get_project, project_id)
        sources = await asyncio.to_thread(
            self.runtime.postgres_store.list_sources,
            project_id=project_id,
            active_only=True,
        )

        source_id_set = set(source_ids or [])
        if source_id_set:
            sources = [source for source in sources if int(source["id"]) in source_id_set]

        if not sources:
            raise ResourceNotFoundError("No matching active sources were found.")

        task = asyncio.create_task(
            self.runtime.collector_worker.run_sources(
                sources,
                per_source_limit=limit_per_source,
            ),
            name=f"collector-project-{project_id}",
        )
        task.add_done_callback(self._log_background_task_result)
        return {
            "status": "started",
            "sources_triggered": len(sources),
        }

    async def get_collector_status(self, project_id: int | None = None) -> dict[str, Any]:
        if project_id is not None:
            await asyncio.to_thread(self.runtime.postgres_store.get_project, project_id)

        sources = await asyncio.to_thread(
            self.runtime.postgres_store.list_sources,
            project_id=project_id,
        )
        now = datetime.now(UTC)
        source_rows = []

        for source in sources:
            last_collected_at = source.get("last_collected_at")
            status = "idle"
            if source.get("last_error"):
                status = "error"
            elif last_collected_at is not None:
                elapsed = (now - last_collected_at).total_seconds()
                status = "stale" if elapsed > source["poll_interval_s"] * 2 else "ok"

            source_rows.append(
                {
                    **source,
                    "raw_posts_count": int(source.get("raw_posts_count", 0)),
                    "status": status,
                }
            )

        queue_size = await asyncio.to_thread(
            self.runtime.postgres_store.count_unprocessed_raw_posts
        )
        return {
            "ml_queue_size": queue_size,
            "sources": source_rows,
        }

    async def get_ml_queue(self, limit: int = 100) -> dict[str, Any]:
        raw_posts = await asyncio.to_thread(
            self.runtime.postgres_store.fetch_unprocessed_raw_posts,
            limit,
        )
        items = self.runtime.ml_normalizer.build_queue_items(raw_posts)
        return {"count": len(items), "items": items}

    async def predict_with_remote_ml(
        self,
        *,
        limit: int = 100,
        persist: bool = True,
    ) -> dict[str, Any]:
        queue = await self.get_ml_queue(limit=limit)
        items = queue["items"]
        if not items:
            return {
                "queued_count": 0,
                "remote_url": self.runtime.external_ml_gateway.predict_url,
                "remote_results_count": 0,
                "stored_count": 0 if persist else None,
                "synced_count": 0 if persist else None,
                "projects": {},
                "persisted": persist,
                "remote_response": {"results": []},
            }

        ml_items, skipped_items = await asyncio.to_thread(
            self.runtime.ml_normalizer.split_queue_items_for_ml,
            items,
        )
        skipped_rows = await asyncio.to_thread(
            self.runtime.ml_normalizer.build_local_irrelevant_rows,
            skipped_items,
        )
        remote_response: dict[str, Any] | list[dict[str, Any]] = {"results": []}
        remote_results: list[dict[str, Any]] = []
        if ml_items:
            remote_response = await self.runtime.external_ml_gateway.predict(ml_items)
            remote_results = self.runtime.ml_normalizer.extract_remote_results(remote_response)

        response_payload = {
            "queued_count": len(items),
            "remote_url": self.runtime.external_ml_gateway.predict_url,
            "remote_results_count": len(remote_results),
            "persisted": persist,
            "remote_response": remote_response,
        }

        if not persist:
            return {
                **response_payload,
                "stored_count": None,
                "synced_count": None,
                "projects": {},
            }

        mention_rows = skipped_rows.copy()
        if ml_items:
            mention_rows.extend(
                await asyncio.to_thread(
                    self.runtime.ml_normalizer.normalize_remote_results,
                    queue_items=ml_items,
                    remote_results=remote_results,
                )
            )
        result = await self.runtime.ml_worker.persist_mention_rows(
            mention_rows,
        )
        return {
            **response_payload,
            "stored_count": result["stored_count"],
            "synced_count": result["synced_count"],
            "projects": {str(key): value for key, value in result["projects"].items()},
        }

    async def submit_ml_results(self, payload) -> dict[str, Any]:
        mention_rows = [
            {
                "raw_post_id": item.raw_post_id,
                "relevance_score": item.relevance_score,
                "relevance_label": item.relevance_label,
                "sentiment_score": item.sentiment_score,
                "sentiment_label": item.sentiment_label,
                "has_risk_words": item.has_risk_words,
                "embedding": item.embedding,
                "dedup_group_id": item.dedup_group_id,
                "is_primary": item.is_primary,
                "processed_at": item.processed_at,
            }
            for item in payload.results
        ]
        result = await self.runtime.ml_worker.persist_mention_rows(
            mention_rows,
        )
        message = "ML results stored and synced to ClickHouse."
        if result["stored_count"] > 0 and result["synced_count"] < result["stored_count"]:
            message = "ML results stored; ClickHouse sync is pending for some rows."
        return {
            "stored_count": result["stored_count"],
            "synced_count": result["synced_count"],
            "projects": {str(key): value for key, value in result["projects"].items()},
            "message": message,
        }

    async def run_local_ml_once(self, limit: int = 100) -> dict[str, Any]:
        result = await self.runtime.ml_worker.run_once(batch_size=limit)
        return {
            **result,
            "projects": {str(key): value for key, value in result["projects"].items()},
        }

    async def list_raw_posts(self, project_id: int, limit: int = 100) -> list[dict[str, Any]]:
        await asyncio.to_thread(self.runtime.postgres_store.get_project, project_id)
        return await asyncio.to_thread(
            self.runtime.postgres_store.list_raw_posts,
            project_id,
            limit,
        )

    async def list_mentions(
        self,
        project_id: int,
        *,
        page: int = 1,
        page_size: int = 100,
        confidence_threshold: float | None = None,
        published_after: datetime | None = None,
        sentiment_label: str | None = None,
    ) -> dict[str, Any]:
        await asyncio.to_thread(self.runtime.postgres_store.get_project, project_id)
        return await asyncio.to_thread(
            self.runtime.postgres_store.list_mentions,
            project_id,
            page=page,
            page_size=page_size,
            confidence_threshold=confidence_threshold,
            published_after=published_after,
            sentiment_label=sentiment_label,
        )

    async def get_health(self) -> dict[str, Any]:
        postgres_status = "healthy"
        clickhouse_status = "healthy"
        ml_status = "healthy"
        ml_error: str | None = None
        ml_url = self.runtime.external_ml_gateway.predict_url
        queue_size = 0

        try:
            await asyncio.to_thread(self.runtime.postgres_store.ping)
        except Exception:
            postgres_status = "unhealthy"

        try:
            await asyncio.to_thread(self.runtime.clickhouse_store.ping)
        except Exception:
            clickhouse_status = "unhealthy"

        if postgres_status == "healthy":
            try:
                queue_size = await asyncio.to_thread(
                    self.runtime.postgres_store.count_unprocessed_raw_posts
                )
            except Exception:
                postgres_status = "unhealthy"

        try:
            ml_health = await self.runtime.external_ml_gateway.get_health_status()
            ml_status = ml_health["status"]
            ml_error = ml_health.get("error")
            ml_url = ml_health.get("url", ml_url)
        except Exception as exc:
            ml_status = "unhealthy"
            ml_error = str(exc)

        if (
            postgres_status == "healthy"
            and clickhouse_status == "healthy"
            and ml_status == "healthy"
        ):
            overall = "healthy"
        elif postgres_status == "unhealthy" and clickhouse_status == "unhealthy":
            overall = "unhealthy"
        else:
            overall = "degraded"

        return {
            "status": overall,
            "postgres": postgres_status,
            "clickhouse": clickhouse_status,
            "ml": ml_status,
            "ml_url": ml_url,
            "ml_error": ml_error,
            "ml_queue_size": queue_size,
        }

    @staticmethod
    def _log_background_task_result(task: asyncio.Task) -> None:
        try:
            task.result()
        except Exception:
            logger.exception("Background collector task failed.")
