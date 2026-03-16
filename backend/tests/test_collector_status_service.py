from __future__ import annotations

import asyncio
import unittest
from datetime import UTC, datetime
from types import SimpleNamespace

from backend.app.modules.brandradar.service import BrandRadarService


class _CollectorStatusStore:
    def get_project(self, project_id: int) -> dict:
        return {"id": project_id, "name": "Demo"}

    def list_sources(self, *, project_id: int | None = None) -> list[dict]:
        now = datetime.now(UTC)
        return [
            {
                "id": 1,
                "project_id": project_id or 1,
                "source_type": "rss",
                "source_config": {"url": "https://example.com/feed.xml"},
                "is_active": True,
                "poll_interval_s": 60,
                "last_collected_at": now,
                "last_error": None,
                "raw_posts_count": 5,
            }
        ]

    def get_raw_post_processing_stats(self, project_id: int | None = None) -> dict[str, int]:
        return {
            "total": 5,
            "processed": 3,
            "pending": 2,
            "failed": 0,
        }


class CollectorStatusServiceTests(unittest.TestCase):
    def test_get_collector_status_reports_processing_progress(self) -> None:
        runtime = SimpleNamespace(postgres_store=_CollectorStatusStore())
        service = BrandRadarService(runtime)

        result = asyncio.run(service.get_collector_status(project_id=7))

        self.assertEqual(result["ml_queue_size"], 2)
        self.assertEqual(result["raw_posts_total"], 5)
        self.assertEqual(result["raw_posts_processed"], 3)
        self.assertEqual(result["raw_posts_pending"], 2)
        self.assertEqual(result["raw_posts_failed"], 0)
        self.assertEqual(result["processing_status"], "processing")
        self.assertEqual(result["sources"][0]["status"], "ok")
