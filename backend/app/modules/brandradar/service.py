from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from backend.app.core.exceptions import ExternalMLServiceError, ResourceNotFoundError
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
        return await asyncio.to_thread(
            self.runtime.postgres_store.update_project,
            project_id,
            name=payload.name,
            keywords=payload.keywords,
            exclude_keywords=payload.exclude_keywords,
            risk_words=payload.risk_words,
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

    async def run_collector_once(
        self,
        *,
        project_id: int | None = None,
        source_ids: list[int] | None = None,
        limit_per_source: int | None = None,
    ) -> dict[str, Any]:
        if project_id is not None:
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

        return await self.runtime.collector_worker.run_sources(
            sources,
            per_source_limit=limit_per_source,
        )

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
        rows = await asyncio.to_thread(
            self.runtime.postgres_store.fetch_unprocessed_raw_posts,
            limit,
        )
        items = [
            {
                "raw_post_id": int(row["id"]),
                "source_id": int(row["source_id"]),
                "project_id": int(row["project_id"]),
                "source_type": row["source_type"],
                "external_id": row["external_id"],
                "url": row["url"],
                "title": row["title"],
                "text": row["text"],
                "author": row["author"],
                "published_at": row["published_at"],
                "collected_at": row["collected_at"],
                "raw_meta": row["raw_meta"],
                "keywords": row["keywords"],
                "exclude_keywords": row["exclude_keywords"],
                "risk_words": row["risk_words"],
            }
            for row in rows
        ]
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
                "remote_response": {"items": []},
            }

        remote_response = await self.runtime.external_ml_gateway.predict(items)
        remote_results = self._extract_remote_results(remote_response)

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

        mention_rows = await asyncio.to_thread(
            self._normalize_remote_results,
            queue_items=items,
            remote_results=remote_results,
        )
        result = await asyncio.to_thread(
            self.runtime.postgres_store.persist_mentions,
            mention_rows,
            self.runtime.clickhouse_store.insert_mention_events,
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
        result = await asyncio.to_thread(
            self.runtime.postgres_store.persist_mentions,
            mention_rows,
            self.runtime.clickhouse_store.insert_mention_events,
        )
        return {
            "stored_count": result["stored_count"],
            "synced_count": result["synced_count"],
            "projects": {str(key): value for key, value in result["projects"].items()},
            "message": "ML results stored and synced to ClickHouse.",
        }

    async def run_local_ml_once(self, limit: int = 100) -> dict[str, Any]:
        result = await asyncio.to_thread(self.runtime.ml_pipeline.process_batch, limit)
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

    async def list_mentions(self, project_id: int, limit: int = 100) -> list[dict[str, Any]]:
        await asyncio.to_thread(self.runtime.postgres_store.get_project, project_id)
        return await asyncio.to_thread(
            self.runtime.postgres_store.list_mentions,
            project_id,
            limit,
        )

    async def get_health(self) -> dict[str, Any]:
        postgres_status = "healthy"
        clickhouse_status = "healthy"
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

        if postgres_status == "healthy" and clickhouse_status == "healthy":
            overall = "healthy"
        elif postgres_status == "unhealthy" and clickhouse_status == "unhealthy":
            overall = "unhealthy"
        else:
            overall = "degraded"

        return {
            "status": overall,
            "postgres": postgres_status,
            "clickhouse": clickhouse_status,
            "ml_queue_size": queue_size,
        }

    @staticmethod
    def _log_background_task_result(task: asyncio.Task) -> None:
        try:
            task.result()
        except Exception:
            logger.exception("Background collector task failed.")

    def _extract_remote_results(self, remote_response: Any) -> list[dict[str, Any]]:
        if isinstance(remote_response, list):
            results = remote_response
        elif isinstance(remote_response, dict):
            for key in ("results", "items", "predictions", "data"):
                value = remote_response.get(key)
                if isinstance(value, list):
                    results = value
                    break
            else:
                raise ExternalMLServiceError(
                    "External ML response must contain a list in one of: results, items, predictions, data."
                )
        else:
            raise ExternalMLServiceError("External ML response has unsupported format.")

        if not all(isinstance(item, dict) for item in results):
            raise ExternalMLServiceError("External ML response items must be JSON objects.")
        return results

    def _normalize_remote_results(
        self,
        *,
        queue_items: list[dict[str, Any]],
        remote_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        queue_by_raw_post_id = {int(item["raw_post_id"]): item for item in queue_items}
        normalized_rows: list[dict[str, Any]] = []

        for index, result in enumerate(remote_results):
            queue_item = self._resolve_queue_item(
                queue_items=queue_items,
                queue_by_raw_post_id=queue_by_raw_post_id,
                remote_item=result,
                index=index,
            )

            relevance_label = self._normalize_relevance_label(result, queue_item)
            relevance_score = self._normalize_float(
                result,
                keys=("relevance_score", "score", "relevance_probability"),
                default=1.0 if relevance_label == "relevant" else 0.0,
            )
            sentiment_label = self._normalize_sentiment_label(result)
            sentiment_score = self._normalize_float(
                result,
                keys=("sentiment_score", "sentiment_value", "polarity"),
                default=0.0,
            )
            has_risk_words = bool(
                result.get(
                    "has_risk_words",
                    self._contains_any(queue_item["text"], queue_item["risk_words"]),
                )
            )
            embedding = self._normalize_embedding(result.get("embedding"), queue_item["text"])

            dedup_group_id = result.get("dedup_group_id")
            is_primary_value = result.get("is_primary")
            if is_primary_value is None:
                dedup = (
                    self.runtime.ml_pipeline.deduplicator.assign(
                        int(queue_item["project_id"]),
                        embedding,
                    )
                    if relevance_label == "relevant"
                    else None
                )
                dedup_group_id = (
                    dedup_group_id
                    if dedup_group_id is not None
                    else (dedup.dedup_group_id if dedup else None)
                )
                is_primary = dedup.is_primary if dedup else True
            else:
                is_primary = bool(is_primary_value)

            normalized_rows.append(
                {
                    "raw_post_id": int(queue_item["raw_post_id"]),
                    "project_id": int(queue_item["project_id"]),
                    "relevance_score": relevance_score,
                    "relevance_label": relevance_label,
                    "sentiment_score": sentiment_score,
                    "sentiment_label": sentiment_label,
                    "has_risk_words": has_risk_words,
                    "embedding": embedding,
                    "dedup_group_id": int(dedup_group_id) if dedup_group_id is not None else None,
                    "is_primary": is_primary,
                    "processed_at": self._parse_datetime(result.get("processed_at")),
                }
            )

        return normalized_rows

    @staticmethod
    def _resolve_queue_item(
        *,
        queue_items: list[dict[str, Any]],
        queue_by_raw_post_id: dict[int, dict[str, Any]],
        remote_item: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        raw_post_id = remote_item.get("raw_post_id")
        if raw_post_id is not None:
            matched = queue_by_raw_post_id.get(int(raw_post_id))
            if matched is None:
                raise ExternalMLServiceError(
                    f"External ML returned unknown raw_post_id={raw_post_id}."
                )
            return matched

        if index >= len(queue_items):
            raise ExternalMLServiceError(
                "External ML returned more results than queued items and some results have no raw_post_id."
            )
        return queue_items[index]

    @staticmethod
    def _normalize_float(
        payload: dict[str, Any],
        *,
        keys: tuple[str, ...],
        default: float,
    ) -> float:
        for key in keys:
            value = payload.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return float(default)

    @staticmethod
    def _normalize_relevance_label(
        payload: dict[str, Any],
        queue_item: dict[str, Any],
    ) -> str:
        raw_value = payload.get("relevance_label", payload.get("relevance"))
        if isinstance(raw_value, bool):
            return "relevant" if raw_value else "irrelevant"
        if isinstance(raw_value, str):
            normalized = raw_value.strip().casefold()
            if normalized in {"relevant", "relevance", "true", "1", "yes"}:
                return "relevant"
            if normalized in {"irrelevant", "false", "0", "no"}:
                return "irrelevant"

        if "is_relevant" in payload:
            return "relevant" if bool(payload["is_relevant"]) else "irrelevant"

        normalized_text = " ".join(queue_item["text"].casefold().split())
        if any(" ".join(word.casefold().split()) in normalized_text for word in queue_item["keywords"]):
            return "relevant"
        return "irrelevant"

    @staticmethod
    def _normalize_sentiment_label(payload: dict[str, Any]) -> str:
        raw_value = payload.get("sentiment_label", payload.get("sentiment"))
        if isinstance(raw_value, str):
            normalized = raw_value.strip().casefold()
            if normalized in {"positive", "neutral", "negative"}:
                return normalized
        return "neutral"

    def _normalize_embedding(
        self,
        embedding: Any,
        text: str,
    ) -> list[float]:
        if isinstance(embedding, list) and len(embedding) == 384:
            try:
                return [float(value) for value in embedding]
            except (TypeError, ValueError):
                pass
        return self.runtime.ml_pipeline.embeddings.encode(text)

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    @staticmethod
    def _contains_any(text: str, words: list[str]) -> bool:
        normalized = " ".join(text.casefold().split())
        return any(" ".join(word.casefold().split()) in normalized for word in words)
