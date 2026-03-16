from __future__ import annotations

import unittest
from datetime import UTC, datetime
from typing import Any

from backend.app.core.exceptions import ExternalMLResponseError
from backend.app.ml.normalizer import MLResultNormalizer


class _DedupFreeStore:
    def find_similar_mentions(
        self,
        project_id: int,
        embedding: list[float],
    ) -> list[dict[str, Any]]:
        return []


class MLResultNormalizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.normalizer = MLResultNormalizer(_DedupFreeStore())
        now = datetime.now(UTC)
        self.queue_items = [
            {
                "raw_post_id": 1,
                "source_id": 10,
                "project_id": 100,
                "source_type": "rss",
                "external_id": "post-1",
                "url": "https://example.com/1",
                "title": "Relevant post",
                "text": "Brand outage update",
                "author": "Alice",
                "published_at": now,
                "collected_at": now,
                "raw_meta": {},
                "keywords": ["brand"],
                "exclude_keywords": [],
                "risk_words": ["outage"],
            },
            {
                "raw_post_id": 2,
                "source_id": 10,
                "project_id": 100,
                "source_type": "rss",
                "external_id": "post-2",
                "url": "https://example.com/2",
                "title": "Missing keyword",
                "text": "Service outage update",
                "author": "Bob",
                "published_at": now,
                "collected_at": now,
                "raw_meta": {},
                "keywords": ["brand"],
                "exclude_keywords": [],
                "risk_words": ["outage"],
            },
            {
                "raw_post_id": 3,
                "source_id": 10,
                "project_id": 100,
                "source_type": "rss",
                "external_id": "post-3",
                "url": "https://example.com/3",
                "title": "Excluded post",
                "text": "Brand internal memo",
                "author": "Carol",
                "published_at": now,
                "collected_at": now,
                "raw_meta": {},
                "keywords": ["brand"],
                "exclude_keywords": ["internal"],
                "risk_words": ["outage"],
            },
            {
                "raw_post_id": 4,
                "source_id": 10,
                "project_id": 100,
                "source_type": "rss",
                "external_id": "post-4",
                "url": "https://example.com/4",
                "title": "No keyword gate",
                "text": "General company update",
                "author": "Dave",
                "published_at": now,
                "collected_at": now,
                "raw_meta": {},
                "keywords": [],
                "exclude_keywords": [],
                "risk_words": ["outage"],
            },
        ]

    def test_normalize_remote_results_applies_local_keyword_exclude_and_risk_rules(self) -> None:
        remote_results = [
            self._remote_result(),
            self._remote_result(),
            self._remote_result(),
            self._remote_result(),
        ]

        normalized = self.normalizer.normalize_remote_results(
            queue_items=self.queue_items,
            remote_results=remote_results,
        )

        self.assertEqual(normalized[0]["relevance_label"], "relevant")
        self.assertEqual(normalized[0]["relevance_score"], 0.91)
        self.assertTrue(normalized[0]["has_risk_words"])
        self.assertIsNone(normalized[0]["embedding"])

        self.assertEqual(normalized[1]["relevance_label"], "irrelevant")
        self.assertEqual(normalized[1]["relevance_score"], 0.0)
        self.assertTrue(normalized[1]["has_risk_words"])

        self.assertEqual(normalized[2]["relevance_label"], "irrelevant")
        self.assertEqual(normalized[2]["relevance_score"], 0.0)
        self.assertFalse(normalized[2]["has_risk_words"])

        self.assertEqual(normalized[3]["relevance_label"], "relevant")
        self.assertEqual(normalized[3]["relevance_score"], 0.91)
        self.assertFalse(normalized[3]["has_risk_words"])

    def test_normalize_remote_results_rejects_partial_results_without_raw_post_id(self) -> None:
        with self.assertRaisesRegex(
            ExternalMLResponseError,
            "different number of results",
        ):
            self.normalizer.normalize_remote_results(
                queue_items=self.queue_items[:2],
                remote_results=[self._remote_result()],
            )

    def test_normalize_remote_results_rejects_empty_results_without_raw_post_id(self) -> None:
        with self.assertRaisesRegex(
            ExternalMLResponseError,
            "returned no results",
        ):
            self.normalizer.normalize_remote_results(
                queue_items=self.queue_items[:1],
                remote_results=[],
            )

    @staticmethod
    def _remote_result() -> dict[str, Any]:
        return {
            "is_relevant": True,
            "relevance_score": 0.91,
            "sentiment": "neutral",
            "sentiment_score": 0.11,
            "has_risk_words": False,
        }
