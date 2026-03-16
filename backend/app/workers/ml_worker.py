from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from backend.app.core.exceptions import ExternalMLRequestError

if TYPE_CHECKING:
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
        idle_sleep_seconds: float = 2.0,
    ):
        self.store = store
        self.clickhouse_store = clickhouse_store
        self.gateway = gateway
        self.normalizer = normalizer
        self.batch_size = batch_size
        self.idle_sleep_seconds = idle_sleep_seconds

    async def persist_mention_rows(self, mention_rows: list[dict[str, Any]]) -> dict[str, Any]:
        result = await asyncio.to_thread(
            self.store.persist_mentions,
            mention_rows,
        )
        synced_count = await self.sync_mention_rows(result["sync_rows"])
        return {
            "stored_count": result["stored_count"],
            "synced_count": synced_count,
            "projects": result["projects"],
        }

    async def sync_pending_mentions(self, limit: int | None = None) -> int:
        fetch_limit = limit if limit is not None else self.batch_size
        pending_rows = await asyncio.to_thread(
            self.store.fetch_pending_mention_events,
            fetch_limit,
        )
        return await self.sync_mention_rows(pending_rows)

    async def sync_mention_rows(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0

        mention_ids = [int(row["mention_id"]) for row in rows]

        try:
            await asyncio.to_thread(self.clickhouse_store.insert_mention_events, rows)
        except Exception:
            logger.exception(
                "ClickHouse mention sync failed for %s rows; leaving them pending.",
                len(rows),
            )
            return 0

        for attempt in range(3):
            try:
                await asyncio.to_thread(
                    self.store.mark_mentions_clickhouse_synced,
                    mention_ids,
                )
                return len(rows)
            except Exception:
                if attempt == 2:
                    logger.exception(
                        "Stored mention rows in ClickHouse but failed to mark %s rows as synced in Postgres.",
                        len(rows),
                    )
                    return 0
                await asyncio.sleep(0.5)

        return 0

    async def run_once(self, batch_size: int | None = None) -> dict[str, Any]:
        return await self._run_once(batch_size=batch_size, project_id=None)

    async def run_until_project_queue_drained(
        self,
        project_id: int,
        *,
        batch_size: int | None = None,
        max_batches: int = 100,
    ) -> dict[str, Any]:
        effective_batch_size = batch_size if batch_size is not None else self.batch_size
        aggregated_projects: dict[int, dict[str, int]] = {}
        total_batch_size = 0
        total_stored_count = 0
        total_synced_count = 0

        for _ in range(max_batches):
            result = await self._run_once(
                batch_size=effective_batch_size,
                project_id=project_id,
            )
            total_batch_size += result["batch_size"]
            total_stored_count += result["stored_count"]
            total_synced_count += result["synced_count"]

            for project_key, stats in result["projects"].items():
                aggregated = aggregated_projects.setdefault(
                    int(project_key),
                    {
                        "batch_size": 0,
                        "relevant_count": 0,
                        "irrelevant_count": 0,
                        "dedup_count": 0,
                    },
                )
                for key in ("batch_size", "relevant_count", "irrelevant_count", "dedup_count"):
                    aggregated[key] += int(stats.get(key, 0))

            if result["batch_size"] == 0:
                break

        return {
            "batch_size": total_batch_size,
            "stored_count": total_stored_count,
            "synced_count": total_synced_count,
            "projects": aggregated_projects,
        }

    async def _run_once(
        self,
        *,
        batch_size: int | None,
        project_id: int | None,
    ) -> dict[str, Any]:
        effective_batch_size = batch_size if batch_size is not None else self.batch_size
        synced_count = await self.sync_pending_mentions(limit=effective_batch_size)
        if project_id is None:
            raw_posts = await asyncio.to_thread(
                self.store.fetch_unprocessed_raw_posts,
                effective_batch_size,
            )
        else:
            raw_posts = await asyncio.to_thread(
                self.store.fetch_unprocessed_raw_posts,
                effective_batch_size,
                project_id=project_id,
            )
        queue_items = self.normalizer.build_queue_items(raw_posts)
        if not queue_items:
            return {
                "batch_size": 0,
                "stored_count": 0,
                "synced_count": synced_count,
                "projects": {},
            }

        mention_rows, failures = await self._process_queue_items(queue_items)
        if failures:
            failed_count = await asyncio.to_thread(
                self.store.mark_raw_posts_ml_failed,
                failures,
            )
            logger.warning("Marked %s raw posts as ML-failed.", failed_count)

        if not mention_rows:
            return {
                "batch_size": len(queue_items),
                "stored_count": 0,
                "synced_count": synced_count,
                "projects": {},
            }

        result = await self.persist_mention_rows(mention_rows)
        return {
            "batch_size": len(queue_items),
            "stored_count": result["stored_count"],
            "synced_count": synced_count + result["synced_count"],
            "projects": result["projects"],
        }

    async def _process_queue_items(
        self,
        queue_items: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        try:
            mention_rows = await self._predict_and_normalize(queue_items)
            return mention_rows, []
        except Exception as exc:
            if len(queue_items) == 1:
                if self._is_transient_ml_error(exc):
                    raise
                return [], [self._build_failure(queue_items[0], exc)]

            logger.warning(
                "ML batch prediction failed for %s rows; retrying one-by-one: %s",
                len(queue_items),
                exc,
            )

        mention_rows: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []
        transient_errors: list[Exception] = []

        for item in queue_items:
            try:
                mention_rows.extend(await self._predict_and_normalize([item]))
            except Exception as exc:
                if self._is_transient_ml_error(exc):
                    transient_errors.append(exc)
                    logger.warning(
                        "Transient ML failure for raw_post_id=%s; leaving it in the queue: %s",
                        item["raw_post_id"],
                        exc,
                    )
                    continue
                failures.append(self._build_failure(item, exc))

        if transient_errors and not mention_rows and not failures:
            raise transient_errors[0]

        for failure in failures:
            logger.warning(
                "ML failed for raw_post_id=%s: %s",
                failure["raw_post_id"],
                failure["error"],
            )

        return mention_rows, [
            {
                "raw_post_id": failure["raw_post_id"],
                "error": failure["error"],
            }
            for failure in failures
        ]

    async def _predict_and_normalize(
        self,
        queue_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        ml_queue_items, skipped_queue_items = await asyncio.to_thread(
            self.normalizer.split_queue_items_for_ml,
            queue_items,
        )
        mention_rows = await asyncio.to_thread(
            self.normalizer.build_local_irrelevant_rows,
            skipped_queue_items,
        )
        if not ml_queue_items:
            return mention_rows

        remote_response = await self.gateway.predict(ml_queue_items)
        remote_results = self.normalizer.extract_remote_results(remote_response)
        ml_rows = await asyncio.to_thread(
            self.normalizer.normalize_remote_results,
            queue_items=ml_queue_items,
            remote_results=remote_results,
        )
        return mention_rows + ml_rows

    @staticmethod
    def _build_failure(queue_item: dict[str, Any], exc: Exception) -> dict[str, Any]:
        error_message = f"{type(exc).__name__}: {exc}".strip()
        return {
            "raw_post_id": int(queue_item["raw_post_id"]),
            "error": error_message[:1000],
            "exception": exc,
        }

    @staticmethod
    def _is_transient_ml_error(exc: Exception) -> bool:
        if not isinstance(exc, ExternalMLRequestError):
            return False

        if exc.status_code is None:
            return True

        return exc.status_code >= 500 or exc.status_code in {408, 429}

    async def run_forever(self, stop_event: asyncio.Event | None = None) -> None:
        event = stop_event or asyncio.Event()

        while not event.is_set():
            should_idle_sleep = True
            try:
                result = await self.run_once()
                should_idle_sleep = result["batch_size"] == 0
            except Exception:
                logger.exception("ML worker iteration failed.")
            if not should_idle_sleep:
                continue
            try:
                await asyncio.wait_for(event.wait(), timeout=self.idle_sleep_seconds)
            except TimeoutError:
                continue
