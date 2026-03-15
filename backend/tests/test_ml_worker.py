from __future__ import annotations

import unittest
from datetime import UTC, datetime
from typing import Any

from backend.app.core.exceptions import ExternalMLRequestError, ExternalMLResponseError
from backend.app.ml.normalizer import MLResultNormalizer
from backend.app.workers.ml_worker import MLWorker


class _DedupFreeStore:
    def find_similar_mentions(self, project_id: int, embedding: list[float]) -> list[dict[str, Any]]:
        return []


class _WorkerStore(_DedupFreeStore):
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.raw_posts = [
            {
                "id": 1,
                "source_id": 10,
                "project_id": 100,
                "source_type": "rss",
                "external_id": "post-1",
                "url": "https://example.com/1",
                "title": "Good post",
                "text": "brand update",
                "author": "Alice",
                "published_at": now,
                "collected_at": now,
                "raw_meta": {},
                "keywords": ["brand"],
                "exclude_keywords": [],
                "risk_words": ["outage"],
            },
            {
                "id": 2,
                "source_id": 10,
                "project_id": 100,
                "source_type": "rss",
                "external_id": "post-2",
                "url": "https://example.com/2",
                "title": "Bad post",
                "text": "brand outage",
                "author": "Bob",
                "published_at": now,
                "collected_at": now,
                "raw_meta": {},
                "keywords": ["brand"],
                "exclude_keywords": [],
                "risk_words": ["outage"],
            },
        ]
        self.failed_rows: list[dict[str, Any]] = []
        self.persisted_rows: list[dict[str, Any]] = []
        self.synced_mentions: list[int] = []

    def fetch_unprocessed_raw_posts(self, limit: int) -> list[dict[str, Any]]:
        return self.raw_posts[:limit]

    def fetch_pending_mention_events(self, limit: int) -> list[dict[str, Any]]:
        return []

    def mark_raw_posts_ml_failed(self, failures: list[dict[str, Any]]) -> int:
        self.failed_rows.extend(failures)
        return len(failures)

    def persist_mentions(self, mention_rows: list[dict[str, Any]]) -> dict[str, Any]:
        self.persisted_rows.extend(mention_rows)
        sync_rows = [
            {
                "mention_id": index + 1000,
                "project_id": row["project_id"],
                "source_type": "rss",
                "source_id": 10,
                "author": "Alice",
                "relevance_score": row["relevance_score"],
                "relevance_label": row["relevance_label"],
                "sentiment_score": row["sentiment_score"],
                "sentiment_label": row["sentiment_label"],
                "has_risk_words": int(bool(row["has_risk_words"])),
                "is_primary": int(bool(row["is_primary"])),
                "published_at": datetime.now(UTC),
                "collected_at": datetime.now(UTC),
                "processed_at": row["processed_at"] or datetime.now(UTC),
                "dedup_group_id": int(row["dedup_group_id"] or 0),
            }
            for index, row in enumerate(mention_rows)
        ]
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
            "sync_rows": sync_rows,
        }

    def mark_mentions_clickhouse_synced(self, mention_ids: list[int]) -> int:
        self.synced_mentions.extend(mention_ids)
        return len(mention_ids)


class _SyncStore(_DedupFreeStore):
    def __init__(self, call_order: list[str]) -> None:
        self.call_order = call_order

    def persist_mentions(self, mention_rows: list[dict[str, Any]]) -> dict[str, Any]:
        self.call_order.append("persist")
        return {
            "stored_count": len(mention_rows),
            "projects": {1: {"batch_size": len(mention_rows), "relevant_count": 1, "irrelevant_count": 0, "dedup_count": 0}},
            "sync_rows": [
                {
                    "mention_id": 501,
                    "project_id": 1,
                    "source_type": "rss",
                    "source_id": 1,
                    "author": "",
                    "relevance_score": 0.99,
                    "relevance_label": "relevant",
                    "sentiment_score": 0.0,
                    "sentiment_label": "neutral",
                    "has_risk_words": 0,
                    "is_primary": 1,
                    "published_at": datetime.now(UTC),
                    "collected_at": datetime.now(UTC),
                    "processed_at": datetime.now(UTC),
                    "dedup_group_id": 0,
                }
            ],
        }

    def mark_mentions_clickhouse_synced(self, mention_ids: list[int]) -> int:
        self.call_order.append("mark")
        return len(mention_ids)


class _GatewayWithBadItem:
    async def predict(self, items: list[dict[str, Any]]) -> Any:
        raw_post_id = items[0]["raw_post_id"]
        if len(items) > 1:
            raise ExternalMLResponseError("batch payload mismatch")
        if raw_post_id == 1:
            return {
                "items": [
                    {
                        "raw_post_id": 1,
                        "relevance_label": "relevant",
                        "relevance_score": 0.97,
                        "sentiment_label": "neutral",
                        "sentiment_score": 0.12,
                        "embedding": [0.01] * 384,
                    }
                ]
            }
        return {
            "items": [
                {
                    "raw_post_id": 2,
                    "relevance_label": "relevant",
                    "embedding": [0.5, 0.6],
                }
            ]
        }


class _TransientFailureGateway:
    async def predict(self, items: list[dict[str, Any]]) -> Any:
        raise ExternalMLRequestError("service unavailable", status_code=503)


class _ClickHouseRecorder:
    def __init__(self, call_order: list[str] | None = None) -> None:
        self.call_order = call_order

    def insert_mention_events(self, rows: list[dict[str, Any]]) -> int:
        if self.call_order is not None:
            self.call_order.append("insert")
        return len(rows)


class MLWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_once_isolates_bad_posts_and_marks_them_failed(self) -> None:
        store = _WorkerStore()
        worker = MLWorker(
            store=store,
            clickhouse_store=_ClickHouseRecorder(),
            gateway=_GatewayWithBadItem(),
            normalizer=MLResultNormalizer(store),
            batch_size=10,
        )

        result = await worker.run_once()

        self.assertEqual(result["batch_size"], 2)
        self.assertEqual(result["stored_count"], 1)
        self.assertEqual(result["synced_count"], 1)
        self.assertEqual(len(store.persisted_rows), 1)
        self.assertEqual(store.persisted_rows[0]["raw_post_id"], 1)
        self.assertEqual(store.failed_rows, [{"raw_post_id": 2, "error": "ExternalMLResponseError: External ML result must contain a valid embedding with 384 numeric values."}])
        self.assertEqual(store.synced_mentions, [1000])

    async def test_run_once_keeps_queue_retryable_when_all_failures_are_transient(self) -> None:
        store = _WorkerStore()
        worker = MLWorker(
            store=store,
            clickhouse_store=_ClickHouseRecorder(),
            gateway=_TransientFailureGateway(),
            normalizer=MLResultNormalizer(store),
            batch_size=10,
        )

        with self.assertRaises(ExternalMLRequestError):
            await worker.run_once()

        self.assertEqual(store.failed_rows, [])
        self.assertEqual(store.persisted_rows, [])

    async def test_persist_mention_rows_syncs_after_postgres_persist(self) -> None:
        call_order: list[str] = []
        store = _SyncStore(call_order)
        worker = MLWorker(
            store=store,
            clickhouse_store=_ClickHouseRecorder(call_order),
            gateway=_GatewayWithBadItem(),
            normalizer=MLResultNormalizer(store),
            batch_size=10,
        )

        result = await worker.persist_mention_rows(
            [
                {
                    "raw_post_id": 1,
                    "project_id": 1,
                    "relevance_score": 0.99,
                    "relevance_label": "relevant",
                    "sentiment_score": 0.0,
                    "sentiment_label": "neutral",
                    "has_risk_words": False,
                    "embedding": [0.01] * 384,
                    "dedup_group_id": None,
                    "is_primary": True,
                    "processed_at": datetime.now(UTC),
                }
            ]
        )

        self.assertEqual(result["stored_count"], 1)
        self.assertEqual(result["synced_count"], 1)
        self.assertEqual(call_order, ["persist", "insert", "mark"])
