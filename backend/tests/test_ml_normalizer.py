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
                "company": "Brand Radar",
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
                "company": "Brand Radar",
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
                "company": "Brand Radar",
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
                "company": "Brand Radar",
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

    def test_normalize_remote_results_uses_ml_confidence_alias(self) -> None:
        normalized = self.normalizer.normalize_remote_results(
            queue_items=self.queue_items[:1],
            remote_results=[
                {
                    "company": "Brand Radar",
                    "is_relevant": True,
                    "confidence": 0.73,
                    "sentiment": "neutral",
                    "sentiment_score": 0.11,
                }
            ],
        )

        self.assertEqual(normalized[0]["relevance_label"], "relevant")
        self.assertEqual(normalized[0]["relevance_score"], 0.73)

    def test_normalize_remote_results_uses_sentiment_probability_from_confidence_map(self) -> None:
        normalized = self.normalizer.normalize_remote_results(
            queue_items=self.queue_items[:1],
            remote_results=[
                {
                    "company": "Brand Radar",
                    "sentiment": "negative",
                    "sentiment_score": 0.9419,
                    "confidence": {
                        "negative": 0.9419,
                        "neutral": 0.0298,
                        "positive": 0.0283,
                    },
                }
            ],
        )

        self.assertEqual(normalized[0]["relevance_label"], "relevant")
        self.assertEqual(normalized[0]["sentiment_label"], "negative")
        self.assertEqual(normalized[0]["relevance_score"], 0.9419)

    def test_normalize_remote_results_requires_ml_confidence_for_ml_items(self) -> None:
        with self.assertRaisesRegex(
            ExternalMLResponseError,
            "must contain a valid relevance score",
        ):
            self.normalizer.normalize_remote_results(
                queue_items=self.queue_items[:1],
                remote_results=[
                    {
                        "company": "Brand Radar",
                        "is_relevant": True,
                        "sentiment": "neutral",
                        "sentiment_score": 0.11,
                    }
                ],
            )

    def test_split_queue_items_for_ml_skips_non_matching_and_excluded_items(self) -> None:
        ml_items, skipped_items = self.normalizer.split_queue_items_for_ml(
            self.queue_items,
        )

        self.assertEqual([item["raw_post_id"] for item in ml_items], [1, 4])
        self.assertEqual([item["raw_post_id"] for item in skipped_items], [2, 3])

    def test_build_local_irrelevant_rows_marks_filtered_items_without_ml(self) -> None:
        rows = self.normalizer.build_local_irrelevant_rows(self.queue_items[1:3])

        self.assertEqual([row["raw_post_id"] for row in rows], [2, 3])
        self.assertEqual([row["relevance_label"] for row in rows], ["irrelevant", "irrelevant"])
        self.assertEqual([row["relevance_score"] for row in rows], [0.0, 0.0])
        self.assertEqual([row["sentiment_label"] for row in rows], ["neutral", "neutral"])
        self.assertEqual([row["has_risk_words"] for row in rows], [True, False])
        self.assertEqual([row["embedding"] for row in rows], [None, None])

    @staticmethod
    def _remote_result() -> dict[str, Any]:
        return {
            "company": "Brand Radar",
            "is_relevant": True,
            "relevance_score": 0.91,
            "sentiment": "neutral",
            "sentiment_score": 0.11,
            "has_risk_words": False,
        }
