from __future__ import annotations

import unittest
from datetime import UTC, datetime
from types import SimpleNamespace

from backend.app.core.config import Settings
from backend.app.infra.db.postgres import BrandRadarPostgresStore
from backend.app.ml.normalizer import MLResultNormalizer
from backend.app.modules.brandradar.schemas import ProjectUpdateRequest
from backend.app.modules.brandradar.service import BrandRadarService
from backend.app.workers.ml_worker import MLWorker


class ResetProjectCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, object]] = []
        self.rowcount = 0

    def execute(self, query: str, params=None) -> None:
        normalized_query = " ".join(query.split())
        self.executed.append((normalized_query, params))
        if normalized_query.startswith("DELETE FROM mentions"):
            self.rowcount = 4
            return
        if normalized_query.startswith("DELETE FROM dedup_groups"):
            self.rowcount = 2
            return
        if normalized_query.startswith("UPDATE raw_posts AS rp"):
            self.rowcount = 6
            return
        if normalized_query.startswith("INSERT INTO events"):
            self.rowcount = 1
            return
        raise AssertionError(f"Unexpected query: {normalized_query}")

    def __enter__(self) -> "ResetProjectCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class ResetProjectConnection:
    def __init__(self, cursor: ResetProjectCursor) -> None:
        self._cursor = cursor
        self.commits = 0

    def cursor(self) -> ResetProjectCursor:
        return self._cursor

    def commit(self) -> None:
        self.commits += 1

    def __enter__(self) -> "ResetProjectConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_reset_project_mentions_for_reprocessing_requeues_posts() -> None:
    fake_cursor = ResetProjectCursor()
    fake_connection = ResetProjectConnection(fake_cursor)
    store = BrandRadarPostgresStore(Settings())
    store._connect = lambda *args, **kwargs: fake_connection  # type: ignore[method-assign]
    store._ensure_project_exists = lambda project_id: None  # type: ignore[method-assign]

    result = store.reset_project_mentions_for_reprocessing(3)

    assert result == {
        "mentions_deleted": 4,
        "dedup_groups_deleted": 2,
        "raw_posts_requeued": 6,
    }
    assert fake_connection.commits == 1
    assert [query for query, _ in fake_cursor.executed] == [
        "DELETE FROM mentions WHERE project_id = %s",
        "DELETE FROM dedup_groups WHERE project_id = %s",
        "UPDATE raw_posts AS rp SET ml_processed = FALSE, ml_failed_at = NULL, ml_error = NULL FROM sources s WHERE s.id = rp.source_id AND s.project_id = %s",
        "INSERT INTO events ( project_id, event_type, payload ) VALUES (%s, %s, %s)",
    ]


class RequeueFailedProjectCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, object]] = []
        self.rowcount = 0

    def execute(self, query: str, params=None) -> None:
        normalized_query = " ".join(query.split())
        self.executed.append((normalized_query, params))
        if normalized_query.startswith("UPDATE raw_posts AS rp"):
            self.rowcount = 3
            return
        if normalized_query.startswith("INSERT INTO events"):
            self.rowcount = 1
            return
        raise AssertionError(f"Unexpected query: {normalized_query}")

    def __enter__(self) -> "RequeueFailedProjectCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_requeue_failed_raw_posts_for_reprocessing_retries_only_failed_posts() -> None:
    fake_cursor = RequeueFailedProjectCursor()
    fake_connection = ResetProjectConnection(fake_cursor)
    store = BrandRadarPostgresStore(Settings())
    store._connect = lambda *args, **kwargs: fake_connection  # type: ignore[method-assign]
    store._ensure_project_exists = lambda project_id: None  # type: ignore[method-assign]

    result = store.requeue_failed_raw_posts_for_reprocessing(3)

    assert result == 3
    assert fake_connection.commits == 1
    assert [query for query, _ in fake_cursor.executed] == [
        (
            "UPDATE raw_posts AS rp SET ml_processed = FALSE, ml_failed_at = NULL, "
            "ml_error = NULL FROM sources s WHERE s.id = rp.source_id AND s.project_id = %s "
            "AND rp.ml_processed = FALSE AND rp.ml_failed_at IS NOT NULL"
        ),
        "INSERT INTO events ( project_id, event_type, payload ) VALUES (%s, %s, %s)",
    ]


class _ProjectUpdateStore:
    def __init__(self, *, failed_count: int = 0, requeued_failed_count: int = 0) -> None:
        self.project = {
            "id": 7,
            "name": "Brand Radar",
            "keywords": ["brand"],
            "exclude_keywords": ["internal"],
            "risk_words": ["outage"],
            "created_at": datetime.now(UTC),
            "sources_count": 1,
            "mentions_count": 2,
        }
        self.reset_calls: list[int] = []
        self.failed_requeue_calls: list[int] = []
        self.failed_count = failed_count
        self.requeued_failed_count = requeued_failed_count

    def get_project(self, project_id: int) -> dict:
        assert project_id == 7
        return dict(self.project)

    def update_project(
        self,
        project_id: int,
        *,
        name: str | None = None,
        keywords: list[str] | None = None,
        exclude_keywords: list[str] | None = None,
        risk_words: list[str] | None = None,
    ) -> dict:
        assert project_id == 7
        if name is not None:
            self.project["name"] = name
        if keywords is not None:
            self.project["keywords"] = keywords
        if exclude_keywords is not None:
            self.project["exclude_keywords"] = exclude_keywords
        if risk_words is not None:
            self.project["risk_words"] = risk_words
        return dict(self.project)

    def reset_project_mentions_for_reprocessing(self, project_id: int) -> dict[str, int]:
        self.reset_calls.append(project_id)
        return {
            "mentions_deleted": 2,
            "dedup_groups_deleted": 1,
            "raw_posts_requeued": 5,
        }

    def get_raw_post_processing_stats(self, project_id: int | None = None) -> dict[str, int]:
        assert project_id == 7
        return {
            "total": 7,
            "processed": 2,
            "pending": 1,
            "failed": self.failed_count,
        }

    def requeue_failed_raw_posts_for_reprocessing(self, project_id: int) -> int:
        self.failed_requeue_calls.append(project_id)
        return self.requeued_failed_count


class _RecordingProjectWorker:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.calls: list[int] = []
        self.should_fail = should_fail

    async def run_until_project_queue_drained(self, project_id: int) -> dict:
        self.calls.append(project_id)
        if self.should_fail:
            raise RuntimeError("ml unavailable")
        return {
            "batch_size": 5,
            "stored_count": 5,
            "synced_count": 5,
            "projects": {str(project_id): {"batch_size": 5}},
        }


class ProjectUpdateReprocessingTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_project_reprocesses_feed_when_tracked_words_change(self) -> None:
        store = _ProjectUpdateStore()
        worker = _RecordingProjectWorker()
        service = BrandRadarService(
            SimpleNamespace(
                postgres_store=store,
                ml_worker=worker,
            )
        )

        result = await service.update_project(
            7,
            ProjectUpdateRequest(
                keywords=["brand", "brand radar"],
                exclude_keywords=["internal"],
                risk_words=["outage"],
            ),
        )

        self.assertEqual(result["keywords"], ["brand", "brand radar"])
        self.assertEqual(store.reset_calls, [7])
        self.assertEqual(worker.calls, [7])

    async def test_update_project_skips_reprocessing_when_only_name_changes(self) -> None:
        store = _ProjectUpdateStore()
        worker = _RecordingProjectWorker()
        service = BrandRadarService(
            SimpleNamespace(
                postgres_store=store,
                ml_worker=worker,
            )
        )

        result = await service.update_project(
            7,
            ProjectUpdateRequest(name="Brand Radar 2"),
        )

        self.assertEqual(result["name"], "Brand Radar 2")
        self.assertEqual(store.reset_calls, [])
        self.assertEqual(store.failed_requeue_calls, [])
        self.assertEqual(worker.calls, [])

    async def test_update_project_keeps_project_updated_when_reprocessing_fails(self) -> None:
        store = _ProjectUpdateStore()
        worker = _RecordingProjectWorker(should_fail=True)
        service = BrandRadarService(
            SimpleNamespace(
                postgres_store=store,
                ml_worker=worker,
            )
        )

        result = await service.update_project(
            7,
            ProjectUpdateRequest(
                keywords=["brand", "brand radar"],
            ),
        )

        self.assertEqual(result["keywords"], ["brand", "brand radar"])
        self.assertEqual(store.reset_calls, [7])
        self.assertEqual(store.failed_requeue_calls, [])
        self.assertEqual(worker.calls, [7])

    async def test_update_project_retries_failed_posts_even_when_filters_do_not_change(self) -> None:
        store = _ProjectUpdateStore(failed_count=3, requeued_failed_count=3)
        worker = _RecordingProjectWorker()
        service = BrandRadarService(
            SimpleNamespace(
                postgres_store=store,
                ml_worker=worker,
            )
        )

        result = await service.update_project(
            7,
            ProjectUpdateRequest(name="Brand Radar 2"),
        )

        self.assertEqual(result["name"], "Brand Radar 2")
        self.assertEqual(store.reset_calls, [])
        self.assertEqual(store.failed_requeue_calls, [7])
        self.assertEqual(worker.calls, [7])


class _ProjectScopedStore:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.fetch_calls: list[int | None] = []
        self.persisted_rows: list[dict] = []
        self.pending_rows: list[list[dict]] = [
            [
                {
                    "id": 1,
                    "source_id": 10,
                    "project_id": 100,
                    "source_type": "rss",
                    "project_name": "Brand Radar",
                    "external_id": "post-1",
                    "url": "https://example.com/1",
                    "title": "Brand outage",
                    "text": "brand outage",
                    "author": "Alice",
                    "published_at": now,
                    "collected_at": now,
                    "raw_meta": {},
                    "keywords": ["brand"],
                    "exclude_keywords": [],
                    "risk_words": ["outage"],
                }
            ],
            [],
        ]

    def fetch_unprocessed_raw_posts(
        self,
        limit: int,
        project_id: int | None = None,
    ) -> list[dict]:
        self.fetch_calls.append(project_id)
        return self.pending_rows.pop(0)

    def fetch_pending_mention_events(self, limit: int) -> list[dict]:
        return []

    def persist_mentions(self, mention_rows: list[dict]) -> dict:
        self.persisted_rows.extend(mention_rows)
        return {
            "stored_count": len(mention_rows),
            "projects": {
                100: {
                    "batch_size": len(mention_rows),
                    "relevant_count": len(mention_rows),
                    "irrelevant_count": 0,
                    "dedup_count": 0,
                }
            },
            "sync_rows": [],
        }

    def mark_mentions_clickhouse_synced(self, mention_ids: list[int]) -> int:
        return len(mention_ids)

    def find_similar_mentions(self, project_id: int, embedding: list[float]) -> list[dict]:
        return []


class _ProjectGateway:
    async def predict(self, items: list[dict]) -> dict:
        return {
            "results": [
                {
                    "raw_post_id": int(items[0]["raw_post_id"]),
                    "relevance_label": "relevant",
                    "relevance_score": 0.91,
                    "sentiment_label": "negative",
                    "sentiment_score": 0.75,
                    "embedding": [0.01] * 384,
                }
            ]
        }


class _ProjectClickHouseStore:
    def insert_mention_events(self, rows: list[dict]) -> None:
        return None


class MLWorkerProjectDrainTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_until_project_queue_drained_uses_project_scoped_queue(self) -> None:
        store = _ProjectScopedStore()
        worker = MLWorker(
            store=store,
            clickhouse_store=_ProjectClickHouseStore(),
            gateway=_ProjectGateway(),
            normalizer=MLResultNormalizer(store),
            batch_size=10,
        )

        result = await worker.run_until_project_queue_drained(100)

        self.assertEqual(result["stored_count"], 1)
        self.assertEqual(store.fetch_calls, [100, 100])
        self.assertEqual([row["raw_post_id"] for row in store.persisted_rows], [1])
