from __future__ import annotations

import asyncio
import unittest
from datetime import UTC, datetime, timedelta

from backend.app.workers.collector_worker import CollectorWorker


class _RecordingCollector:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def collect(
        self,
        source: dict[str, object],
        *,
        published_after: datetime | None = None,
    ) -> list[object]:
        self.calls.append(
            {
                "source_id": source["id"],
                "published_after": published_after,
            }
        )
        return []


class _CollectorWorkerStore:
    def __init__(self) -> None:
        self.saved_calls: list[tuple[int, int]] = []
        self.error_calls: list[tuple[int, str]] = []

    def list_due_sources(self) -> list[dict[str, object]]:
        return [{"id": 11, "source_type": "rss"}]

    def save_raw_posts(self, source: dict[str, object], posts: list[object]) -> int:
        self.saved_calls.append((int(source["id"]), len(posts)))
        return len(posts)

    def record_collection_error(self, source: dict[str, object], error: str) -> None:
        self.error_calls.append((int(source["id"]), error))


class _BlockingCollector:
    def __init__(self) -> None:
        self.started_source_ids: list[int] = []
        self.both_started = asyncio.Event()
        self.release = asyncio.Event()

    async def collect(
        self,
        source: dict[str, object],
        *,
        published_after: datetime | None = None,
    ) -> list[object]:
        self.started_source_ids.append(int(source["id"]))
        if len(self.started_source_ids) >= 2:
            self.both_started.set()
        await self.release.wait()
        return []


class CollectorWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_sources_uses_30_day_lookback_by_default(self) -> None:
        collector = _RecordingCollector()
        store = _CollectorWorkerStore()
        worker = CollectorWorker(
            store=store,
            collectors={"rss": collector},
            lookback_days=30,
        )
        before = datetime.now(UTC) - timedelta(days=30, seconds=5)

        result = await worker.run_sources(
            [
                {
                    "id": 11,
                    "source_type": "rss",
                }
            ]
        )
        after = datetime.now(UTC) - timedelta(days=30) + timedelta(seconds=5)

        self.assertEqual(result["sources_processed"], 1)
        self.assertEqual(store.saved_calls, [(11, 0)])
        self.assertEqual(store.error_calls, [])
        self.assertEqual(len(collector.calls), 1)
        published_after = collector.calls[0]["published_after"]
        self.assertIsNotNone(published_after)
        self.assertLessEqual(before, published_after)
        self.assertLessEqual(published_after, after)

    async def test_run_once_uses_due_sources(self) -> None:
        collector = _RecordingCollector()
        store = _CollectorWorkerStore()
        worker = CollectorWorker(
            store=store,
            collectors={"rss": collector},
            lookback_days=30,
        )

        result = await worker.run_once()

        self.assertEqual(result["sources_checked"], 1)
        self.assertEqual(result["sources_processed"], 1)
        self.assertEqual(result["posts_saved"], 0)
        self.assertEqual(store.saved_calls, [(11, 0)])

    async def test_run_sources_accepts_custom_lookback_days(self) -> None:
        collector = _RecordingCollector()
        store = _CollectorWorkerStore()
        worker = CollectorWorker(
            store=store,
            collectors={"rss": collector},
            lookback_days=30,
        )
        before = datetime.now(UTC) - timedelta(days=7, seconds=5)

        await worker.run_sources(
            [
                {
                    "id": 12,
                    "source_type": "rss",
                }
            ],
            lookback_days=7,
        )
        after = datetime.now(UTC) - timedelta(days=7) + timedelta(seconds=5)

        published_after = collector.calls[0]["published_after"]
        self.assertIsNotNone(published_after)
        self.assertLessEqual(before, published_after)
        self.assertLessEqual(published_after, after)

    async def test_run_sources_processes_sources_in_parallel_up_to_limit(self) -> None:
        collector = _BlockingCollector()
        store = _CollectorWorkerStore()
        worker = CollectorWorker(
            store=store,
            collectors={"rss": collector},
            source_concurrency=2,
        )

        run_task = asyncio.create_task(
            worker.run_sources(
                [
                    {"id": 21, "source_type": "rss"},
                    {"id": 22, "source_type": "rss"},
                ]
            )
        )

        await asyncio.wait_for(collector.both_started.wait(), timeout=1.0)
        collector.release.set()
        result = await run_task

        self.assertEqual(result["sources_processed"], 2)
        self.assertEqual(sorted(collector.started_source_ids), [21, 22])
        self.assertEqual(sorted(store.saved_calls), [(21, 0), (22, 0)])
