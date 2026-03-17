from __future__ import annotations

import asyncio
import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from backend.app.core.exceptions import ResourceNotFoundError
from backend.app.modules.brandradar.service import BrandRadarService


class _ServiceStore:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.active_sources = [
            {
                "id": 10,
                "project_id": 1,
                "source_type": "rss",
                "source_config": {"url": "https://example.com/feed.xml"},
                "is_active": True,
                "poll_interval_s": 60,
                "last_collected_at": now,
                "last_error": None,
                "raw_posts_count": 3,
            },
            {
                "id": 20,
                "project_id": 1,
                "source_type": "telegram",
                "source_config": {"channel": "@brand"},
                "is_active": True,
                "poll_interval_s": 60,
                "last_collected_at": now - timedelta(minutes=5),
                "last_error": None,
                "raw_posts_count": "4",
            },
        ]
        self.status_sources = [
            {
                "id": 10,
                "project_id": 1,
                "source_type": "rss",
                "source_config": {"url": "https://example.com/feed.xml"},
                "is_active": True,
                "poll_interval_s": 60,
                "last_collected_at": now,
                "last_error": None,
                "raw_posts_count": 3,
            },
            {
                "id": 20,
                "project_id": 1,
                "source_type": "telegram",
                "source_config": {"channel": "@brand"},
                "is_active": True,
                "poll_interval_s": 60,
                "last_collected_at": now - timedelta(minutes=5),
                "last_error": None,
                "raw_posts_count": "4",
            },
            {
                "id": 30,
                "project_id": 1,
                "source_type": "website",
                "source_config": {"url": "https://example.com/news"},
                "is_active": True,
                "poll_interval_s": 60,
                "last_collected_at": None,
                "last_error": "timeout",
                "raw_posts_count": 1,
            },
            {
                "id": 40,
                "project_id": 1,
                "source_type": "vk",
                "source_config": {"channel": "brand"},
                "is_active": True,
                "poll_interval_s": 60,
                "last_collected_at": None,
                "last_error": None,
                "raw_posts_count": 0,
            },
        ]
        self.raw_posts = [
            {
                "id": 101,
                "source_id": 10,
                "project_id": 1,
                "source_type": "rss",
                "project_name": "Brand Radar",
                "external_id": "post-101",
                "url": "https://example.com/post-101",
                "title": "Brand update",
                "text": "brand update",
                "author": "Alice",
                "published_at": now,
                "collected_at": now,
                "raw_meta": {},
                "keywords": ["brand"],
                "exclude_keywords": [],
                "risk_words": ["outage"],
            }
        ]
        self.processing_stats = {
            "total": 7,
            "processed": 3,
            "pending": 4,
            "failed": 0,
        }
        self.list_mentions_calls: list[dict] = []

    def get_project(self, project_id: int) -> dict:
        if project_id != 1:
            raise ResourceNotFoundError(f"Project {project_id} was not found.")
        return {"id": 1, "name": "Brand Radar"}

    def list_sources(
        self,
        *,
        project_id: int | None = None,
        active_only: bool = False,
    ) -> list[dict]:
        assert project_id == 1
        return list(self.active_sources if active_only else self.status_sources)

    def get_raw_post_processing_stats(self, project_id: int | None = None) -> dict[str, int]:
        assert project_id == 1
        return dict(self.processing_stats)

    def fetch_unprocessed_raw_posts(self, limit: int) -> list[dict]:
        return self.raw_posts[:limit]

    def update_mention_resolved(
        self,
        project_id: int,
        mention_id: int,
        *,
        resolved: bool,
    ) -> dict:
        return {
            "id": mention_id,
            "raw_post_id": 101,
            "project_id": project_id,
            "source_id": 10,
            "source_type": "rss",
            "external_id": "post-101",
            "url": "https://example.com/post-101",
            "title": "Brand update",
            "text": "brand update",
            "author": "Alice",
            "published_at": datetime.now(UTC),
            "collected_at": datetime.now(UTC),
            "relevance_score": 0.88,
            "relevance_label": "relevant",
            "sentiment_score": 0.12,
            "sentiment_label": "neutral",
            "has_risk_words": False,
            "dedup_group_id": None,
            "is_primary": True,
            "resolved": resolved,
            "processed_at": datetime.now(UTC),
        }

    def list_mentions(
        self,
        project_id: int,
        *,
        page: int = 1,
        page_size: int = 100,
        confidence_threshold: float | None = None,
        published_after: datetime | None = None,
        sentiment_label: str | None = None,
        dedup_group_id: int | None = None,
        primary_only: bool = False,
        relevant_only: bool = False,
        include_total: bool = True,
        risk_words_only: bool = False,
    ) -> dict:
        self.list_mentions_calls.append(
            {
                "project_id": project_id,
                "page": page,
                "page_size": page_size,
                "confidence_threshold": confidence_threshold,
                "published_after": published_after,
                "sentiment_label": sentiment_label,
                "dedup_group_id": dedup_group_id,
                "primary_only": primary_only,
                "relevant_only": relevant_only,
                "include_total": include_total,
                "risk_words_only": risk_words_only,
            }
        )
        return {
            "items": [
                {
                    "id": 77,
                    "raw_post_id": 101,
                    "project_id": project_id,
                    "source_id": 10,
                    "source_type": "rss",
                    "external_id": "post-101",
                    "url": "https://example.com/post-101",
                    "title": "Brand update",
                    "text": "brand update",
                    "author": "Alice",
                    "published_at": datetime.now(UTC),
                    "collected_at": datetime.now(UTC),
                    "relevance_score": 0.88,
                    "relevance_label": "relevant",
                    "sentiment_score": 0.12,
                    "sentiment_label": "neutral",
                    "has_risk_words": False,
                    "dedup_group_id": dedup_group_id,
                    "is_primary": False,
                    "resolved": False,
                    "processed_at": datetime.now(UTC),
                }
            ],
            "total": 1,
        }


class _RecordingCollectorWorker:
    def __init__(self) -> None:
        self.calls: list[tuple[list[int], int | None]] = []

    async def run_sources(
        self,
        sources: list[dict],
        *,
        lookback_days: int | None = None,
    ) -> dict:
        self.calls.append(([int(source["id"]) for source in sources], lookback_days))
        return {
            "sources_checked": len(sources),
            "sources_processed": len(sources),
            "posts_saved": 0,
            "errors": [],
        }


class _QueueNormalizer:
    def __init__(self) -> None:
        self.build_calls: list[list[int]] = []
        self.split_calls: list[list[int]] = []
        self.normalize_calls: list[list[int]] = []

    def build_queue_items(self, rows: list[dict]) -> list[dict]:
        self.build_calls.append([int(row["id"]) for row in rows])
        return [
            {
                "raw_post_id": int(row["id"]),
                "project_id": int(row["project_id"]),
                "source_id": int(row["source_id"]),
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

    def split_queue_items_for_ml(self, items: list[dict]) -> tuple[list[dict], list[dict]]:
        self.split_calls.append([int(item["raw_post_id"]) for item in items])
        return items, []

    def build_local_irrelevant_rows(self, items: list[dict]) -> list[dict]:
        return []

    def extract_remote_results(self, response: dict) -> list[dict]:
        return response["results"]

    def normalize_remote_results(
        self,
        *,
        queue_items: list[dict],
        remote_results: list[dict],
    ) -> list[dict]:
        self.normalize_calls.append([int(item["raw_post_id"]) for item in queue_items])
        return [
            {
                "raw_post_id": int(queue_items[0]["raw_post_id"]),
                "project_id": int(queue_items[0]["project_id"]),
                "relevance_score": float(remote_results[0]["relevance_score"]),
                "relevance_label": remote_results[0]["relevance_label"],
                "sentiment_score": float(remote_results[0]["sentiment_score"]),
                "sentiment_label": remote_results[0]["sentiment_label"],
                "has_risk_words": False,
                "embedding": None,
                "dedup_group_id": None,
                "is_primary": True,
                "processed_at": None,
            }
        ]


class _PredictGateway:
    predict_url = "http://ml.example/predict"

    def __init__(self) -> None:
        self.calls: list[list[int]] = []

    async def predict(self, items: list[dict]) -> dict:
        self.calls.append([int(item["raw_post_id"]) for item in items])
        return {
            "results": [
                {
                    "raw_post_id": int(items[0]["raw_post_id"]),
                    "relevance_label": "relevant",
                    "relevance_score": 0.88,
                    "sentiment_label": "neutral",
                    "sentiment_score": 0.12,
                }
            ]
        }


class _PersistingMLWorker:
    def __init__(self, *, synced_count: int) -> None:
        self.synced_count = synced_count
        self.calls: list[list[dict]] = []

    async def persist_mention_rows(self, rows: list[dict]) -> dict:
        self.calls.append(rows)
        return {
            "stored_count": len(rows),
            "synced_count": self.synced_count,
            "projects": {1: {"batch_size": len(rows)}},
        }


class BrandRadarServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_trigger_collector_run_filters_sources_and_starts_background_task(self) -> None:
        store = _ServiceStore()
        collector_worker = _RecordingCollectorWorker()
        runtime = SimpleNamespace(
            postgres_store=store,
            collector_worker=collector_worker,
        )
        service = BrandRadarService(runtime)

        result = await service.trigger_collector_run(
            project_id=1,
            source_ids=[20],
            lookback_days=5,
        )
        await asyncio.sleep(0)

        self.assertEqual(result, {"status": "started", "sources_triggered": 1})
        self.assertEqual(collector_worker.calls, [([20], 5)])

    async def test_trigger_collector_run_raises_when_no_matching_sources(self) -> None:
        store = _ServiceStore()
        runtime = SimpleNamespace(
            postgres_store=store,
            collector_worker=_RecordingCollectorWorker(),
        )
        service = BrandRadarService(runtime)

        with self.assertRaisesRegex(ResourceNotFoundError, "No matching active sources"):
            await service.trigger_collector_run(project_id=1, source_ids=[999])

    async def test_get_collector_status_computes_source_health_and_queue_size(self) -> None:
        store = _ServiceStore()
        runtime = SimpleNamespace(postgres_store=store)
        service = BrandRadarService(runtime)

        result = await service.get_collector_status(project_id=1)

        self.assertEqual(result["ml_queue_size"], 4)
        self.assertEqual(result["raw_posts_total"], 7)
        self.assertEqual(result["raw_posts_processed"], 3)
        self.assertEqual(result["raw_posts_pending"], 4)
        self.assertEqual(result["raw_posts_failed"], 0)
        self.assertEqual(result["processing_status"], "processing")
        self.assertEqual(
            [(item["id"], item["status"], item["raw_posts_count"]) for item in result["sources"]],
            [
                (10, "ok", 3),
                (20, "stale", 4),
                (30, "error", 1),
                (40, "idle", 0),
            ],
        )

    async def test_get_ml_queue_uses_normalizer_output(self) -> None:
        store = _ServiceStore()
        normalizer = _QueueNormalizer()
        runtime = SimpleNamespace(
            postgres_store=store,
            ml_normalizer=normalizer,
        )
        service = BrandRadarService(runtime)

        result = await service.get_ml_queue(limit=10)

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["items"][0]["raw_post_id"], 101)
        self.assertEqual(normalizer.build_calls, [[101]])

    async def test_predict_with_remote_ml_returns_empty_payload_when_queue_is_empty(self) -> None:
        store = _ServiceStore()
        store.raw_posts = []
        runtime = SimpleNamespace(
            postgres_store=store,
            ml_normalizer=_QueueNormalizer(),
            external_ml_gateway=SimpleNamespace(predict_url="http://ml.example/predict"),
        )
        service = BrandRadarService(runtime)

        result = await service.predict_with_remote_ml(limit=5, persist=False)

        self.assertEqual(result["queued_count"], 0)
        self.assertEqual(result["remote_results_count"], 0)
        self.assertEqual(result["remote_response"], {"results": []})
        self.assertIsNone(result["stored_count"])
        self.assertIsNone(result["synced_count"])

    async def test_predict_with_remote_ml_persists_normalized_rows(self) -> None:
        store = _ServiceStore()
        normalizer = _QueueNormalizer()
        gateway = _PredictGateway()
        ml_worker = _PersistingMLWorker(synced_count=1)
        runtime = SimpleNamespace(
            postgres_store=store,
            ml_normalizer=normalizer,
            external_ml_gateway=gateway,
            ml_worker=ml_worker,
        )
        service = BrandRadarService(runtime)

        result = await service.predict_with_remote_ml(limit=5, persist=True)

        self.assertEqual(result["queued_count"], 1)
        self.assertEqual(result["remote_results_count"], 1)
        self.assertEqual(result["stored_count"], 1)
        self.assertEqual(result["synced_count"], 1)
        self.assertEqual(gateway.calls, [[101]])
        self.assertEqual(normalizer.split_calls, [[101]])
        self.assertEqual(normalizer.normalize_calls, [[101]])
        self.assertEqual(ml_worker.calls[0][0]["raw_post_id"], 101)

    async def test_submit_ml_results_reports_partial_sync(self) -> None:
        worker = _PersistingMLWorker(synced_count=0)
        runtime = SimpleNamespace(ml_worker=worker)
        service = BrandRadarService(runtime)
        payload = SimpleNamespace(
            results=[
                SimpleNamespace(
                    raw_post_id=101,
                    relevance_score=0.8,
                    relevance_label="relevant",
                    sentiment_score=0.4,
                    sentiment_label="neutral",
                    has_risk_words=False,
                    embedding=None,
                    dedup_group_id=None,
                    is_primary=True,
                    processed_at=None,
                )
            ]
        )

        result = await service.submit_ml_results(payload)

        self.assertEqual(result["stored_count"], 1)
        self.assertEqual(result["synced_count"], 0)
        self.assertEqual(
            result["message"],
            "ML results stored; ClickHouse sync is pending for some rows.",
        )

    async def test_update_mention_resolved_delegates_to_store(self) -> None:
        store = _ServiceStore()
        runtime = SimpleNamespace(postgres_store=store)
        service = BrandRadarService(runtime)

        result = await service.update_mention_resolved(1, 77, resolved=True)

        self.assertEqual(result["id"], 77)
        self.assertEqual(result["project_id"], 1)
        self.assertTrue(result["resolved"])

    async def test_list_mentions_forwards_dedup_group_and_fast_flags(self) -> None:
        store = _ServiceStore()
        runtime = SimpleNamespace(postgres_store=store)
        service = BrandRadarService(runtime)

        result = await service.list_mentions(
            1,
            page=2,
            page_size=25,
            dedup_group_id=6,
            relevant_only=True,
            include_total=False,
        )

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["dedup_group_id"], 6)
        self.assertEqual(
            store.list_mentions_calls,
            [
                {
                    "project_id": 1,
                    "page": 2,
                    "page_size": 25,
                    "confidence_threshold": None,
                    "published_after": None,
                    "sentiment_label": None,
                    "dedup_group_id": 6,
                    "primary_only": False,
                    "relevant_only": True,
                    "include_total": False,
                    "risk_words_only": False,
                }
            ],
        )
