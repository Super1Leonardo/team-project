from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from backend.app.core.config import Settings
from backend.app.infra.db.postgres import BrandRadarPostgresStore


class FakeCursor:
    def __init__(self, total: int, rows: list[dict]):
        self.total = total
        self.rows = rows
        self.executed: list[tuple[str, object]] = []
        self._fetchone_calls = 0

    def execute(self, query: str, params=None) -> None:
        self.executed.append((query, params))

    def fetchone(self) -> dict:
        self._fetchone_calls += 1
        if self._fetchone_calls == 1:
            return {"total": self.total}
        raise AssertionError("fetchone called unexpectedly")

    def fetchall(self) -> list[dict]:
        return self.rows

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class FakeConnection:
    def __init__(self, cursor: FakeCursor):
        self._cursor = cursor

    def cursor(self) -> FakeCursor:
        return self._cursor

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_list_mentions_filters_before_pagination() -> None:
    published_after = datetime.now(UTC) - timedelta(days=7)
    rows = [
        {
            "id": 1,
            "raw_post_id": 11,
            "project_id": 3,
            "relevance_score": 0.75,
            "relevance_label": "relevant",
            "sentiment_score": 0.65,
            "sentiment_label": "negative",
            "has_risk_words": True,
            "dedup_group_id": None,
            "is_primary": True,
            "resolved": False,
            "processed_at": datetime.now(UTC),
            "source_id": 9,
            "source_type": "telegram",
            "external_id": "x-1",
            "url": "https://example.com/x-1",
            "title": "Title",
            "text": "Body",
            "author": "author",
            "published_at": datetime.now(UTC),
            "collected_at": datetime.now(UTC),
        }
    ]
    fake_cursor = FakeCursor(total=3, rows=rows)
    store = BrandRadarPostgresStore(Settings())
    store._connect = lambda *args, **kwargs: FakeConnection(fake_cursor)  # type: ignore[method-assign]

    result = store.list_mentions(
        3,
        page=2,
        page_size=20,
        confidence_threshold=0.7,
        published_after=published_after,
        sentiment_label="negative",
    )

    assert result["total"] == 3
    assert result["items"] == rows
    assert len(fake_cursor.executed) == 2

    data_query, data_params = fake_cursor.executed[0]
    count_query, count_params = fake_cursor.executed[1]

    assert "LIMIT %s" in data_query
    assert "OFFSET %s" in data_query
    assert "m.sentiment_label = %s" in data_query
    assert data_params == [3, 0.7, published_after, "negative", 20, 20]

    assert "COUNT(*) AS total" in count_query
    assert "m.relevance_score >= %s" in count_query
    assert "rp.published_at >= %s" in count_query
    assert "m.sentiment_label = %s" in count_query
    assert count_params == [3, 0.7, published_after, "negative"]


def test_list_mentions_can_skip_total_count_for_fast_path() -> None:
    rows = [
        {
            "id": 1,
            "raw_post_id": 11,
            "project_id": 3,
            "relevance_score": 0.75,
            "relevance_label": "relevant",
            "sentiment_score": 0.65,
            "sentiment_label": "negative",
            "has_risk_words": True,
            "dedup_group_id": None,
            "is_primary": True,
            "resolved": False,
            "processed_at": datetime.now(UTC),
            "source_id": 9,
            "source_type": "telegram",
            "external_id": "x-1",
            "url": "https://example.com/x-1",
            "title": "Title",
            "text": "Body",
            "author": "author",
            "published_at": datetime.now(UTC),
            "collected_at": datetime.now(UTC),
        }
    ]
    fake_cursor = FakeCursor(total=999, rows=rows)
    store = BrandRadarPostgresStore(Settings())
    store._connect = lambda *args, **kwargs: FakeConnection(fake_cursor)  # type: ignore[method-assign]

    result = store.list_mentions(
        3,
        page=1,
        page_size=50,
        primary_only=True,
        relevant_only=True,
        include_total=False,
    )

    assert result["items"] == rows
    assert result["total"] is None
    assert len(fake_cursor.executed) == 1
    data_query, data_params = fake_cursor.executed[0]
    assert "m.is_primary = TRUE" in data_query
    assert "m.relevance_label = 'relevant'" in data_query
    assert data_params == [3, 50, 0]


def test_list_clusters_groups_similar_mentions_before_pagination() -> None:
    published_after = datetime.now(UTC) - timedelta(days=30)
    rows = [
        {
            "cluster_id": 77,
            "dedup_group_id": 77,
            "mentions_count": 4,
            "first_seen_at": datetime.now(UTC) - timedelta(days=3),
            "last_seen_at": datetime.now(UTC),
            "representative_mention_id": 501,
            "raw_post_id": 11,
            "project_id": 3,
            "relevance_score": 0.88,
            "relevance_label": "relevant",
            "sentiment_score": 0.41,
            "sentiment_label": "negative",
            "has_risk_words": True,
            "source_id": 9,
            "source_type": "telegram",
            "external_id": "x-1",
            "url": "https://example.com/x-1",
            "title": "Cluster title",
            "text": "Cluster body",
            "author": "author",
            "published_at": datetime.now(UTC),
            "collected_at": datetime.now(UTC),
            "processed_at": datetime.now(UTC),
        }
    ]
    fake_cursor = FakeCursor(total=2, rows=rows)
    store = BrandRadarPostgresStore(Settings())
    store._connect = lambda *args, **kwargs: FakeConnection(fake_cursor)  # type: ignore[method-assign]

    result = store.list_clusters(
        3,
        page=2,
        page_size=10,
        confidence_threshold=0.5,
        published_after=published_after,
        sentiment_label="negative",
    )

    assert result["total"] == 2
    assert result["items"] == rows
    assert len(fake_cursor.executed) == 2

    count_query, count_params = fake_cursor.executed[0]
    data_query, data_params = fake_cursor.executed[1]

    assert "WITH filtered_mentions AS" in count_query
    assert "SELECT DISTINCT cluster_id" in count_query
    assert "m.relevance_label = 'relevant'" in count_query
    assert "m.relevance_score >= %s" in count_query
    assert "rp.published_at >= %s" in count_query
    assert "m.sentiment_label = %s" in count_query
    assert count_params == [3, 0.5, published_after, "negative"]

    assert "ROW_NUMBER() OVER" in data_query
    assert "mentions_count" in data_query
    assert "WHERE rc.cluster_rank = 1" in data_query
    assert data_params == [3, 0.5, published_after, "negative", 10, 10]

class PersistMentionsCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, object]] = []
        self._fetchall_calls = 0
        self._fetchone_calls = 0

    def execute(self, query: str, params=None) -> None:
        self.executed.append((" ".join(query.split()), params))

    def fetchall(self) -> list[dict]:
        self._fetchall_calls += 1
        if self._fetchall_calls == 1:
            return [
                {
                    "id": 11,
                    "source_id": 9,
                    "author": "author",
                    "published_at": datetime.now(UTC),
                    "collected_at": datetime.now(UTC),
                    "ml_processed": False,
                    "project_id": 3,
                    "source_type": "telegram",
                }
            ]
        raise AssertionError("fetchall called unexpectedly")

    def fetchone(self) -> dict:
        self._fetchone_calls += 1
        if self._fetchone_calls == 1:
            return {
                "id": 101,
                "raw_post_id": 11,
                "project_id": 3,
                "relevance_score": 0.0,
                "relevance_label": "irrelevant",
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "has_risk_words": False,
                "dedup_group_id": None,
                "is_primary": True,
                "processed_at": datetime.now(UTC),
            }
        raise AssertionError("fetchone called unexpectedly")

    def __enter__(self) -> "PersistMentionsCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class PersistMentionsConnection:
    def __init__(self, cursor: PersistMentionsCursor):
        self._cursor = cursor
        self.commits = 0

    def cursor(self) -> PersistMentionsCursor:
        return self._cursor

    def commit(self) -> None:
        self.commits += 1

    def __enter__(self) -> "PersistMentionsConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_persist_mentions_casts_null_embedding_to_vector_type() -> None:
    fake_cursor = PersistMentionsCursor()
    fake_connection = PersistMentionsConnection(fake_cursor)
    store = BrandRadarPostgresStore(Settings())
    store._connect = lambda *args, **kwargs: fake_connection  # type: ignore[method-assign]

    result = store.persist_mentions(
        [
            {
                "raw_post_id": 11,
                "project_id": 3,
                "relevance_score": 0.0,
                "relevance_label": "irrelevant",
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "has_risk_words": False,
                "embedding": None,
                "dedup_group_id": None,
                "is_primary": True,
                "processed_at": datetime.now(UTC),
            }
        ]
    )

    assert result["stored_count"] == 1
    insert_query, insert_params = fake_cursor.executed[1]
    assert "CAST(%s AS vector)" in insert_query
    assert "WHEN %s IS NULL THEN NULL" not in insert_query
    assert insert_params[7] is None
    assert fake_connection.commits == 1


class MixedPersistMentionsCursor:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.executed: list[tuple[str, object]] = []
        self._rows = [
            {
                "id": 11,
                "source_id": 9,
                "author": "author-1",
                "published_at": now,
                "collected_at": now,
                "ml_processed": True,
                "project_id": 3,
                "source_type": "telegram",
            },
            {
                "id": 12,
                "source_id": 9,
                "author": "author-2",
                "published_at": now,
                "collected_at": now,
                "ml_processed": False,
                "project_id": 3,
                "source_type": "telegram",
            },
        ]
        self._fetchone_calls = 0

    def execute(self, query: str, params=None) -> None:
        self.executed.append((" ".join(query.split()), params))

    def fetchall(self) -> list[dict]:
        return self._rows

    def fetchone(self) -> dict:
        self._fetchone_calls += 1
        if self._fetchone_calls == 1:
            return {
                "id": 202,
                "raw_post_id": 12,
                "project_id": 3,
                "relevance_score": 0.6,
                "relevance_label": "relevant",
                "sentiment_score": 0.1,
                "sentiment_label": "neutral",
                "has_risk_words": False,
                "dedup_group_id": None,
                "is_primary": True,
                "processed_at": datetime.now(UTC),
            }
        raise AssertionError("fetchone called unexpectedly")

    def __enter__(self) -> "MixedPersistMentionsCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class PersistMentionsRepositoryTests(unittest.TestCase):
    def test_persist_mentions_casts_null_embedding_to_vector_type(self) -> None:
        fake_cursor = PersistMentionsCursor()
        fake_connection = PersistMentionsConnection(fake_cursor)
        store = BrandRadarPostgresStore(Settings())
        store._connect = lambda *args, **kwargs: fake_connection  # type: ignore[method-assign]

        result = store.persist_mentions(
            [
                {
                    "raw_post_id": 11,
                    "project_id": 3,
                    "relevance_score": 0.0,
                    "relevance_label": "irrelevant",
                    "sentiment_score": 0.0,
                    "sentiment_label": "neutral",
                    "has_risk_words": False,
                    "embedding": None,
                    "dedup_group_id": None,
                    "is_primary": True,
                    "processed_at": datetime.now(UTC),
                }
            ]
        )

        self.assertEqual(result["stored_count"], 1)
        insert_query, insert_params = fake_cursor.executed[1]
        self.assertIn("CAST(%s AS vector)", insert_query)
        self.assertNotIn("WHEN %s IS NULL THEN NULL", insert_query)
        self.assertIsNone(insert_params[7])
        self.assertEqual(fake_connection.commits, 1)

    def test_persist_mentions_skips_rows_already_processed_by_another_worker(self) -> None:
        fake_cursor = MixedPersistMentionsCursor()
        fake_connection = PersistMentionsConnection(fake_cursor)
        store = BrandRadarPostgresStore(Settings())
        store._connect = lambda *args, **kwargs: fake_connection  # type: ignore[method-assign]

        result = store.persist_mentions(
            [
                {
                    "raw_post_id": 11,
                    "project_id": 3,
                    "relevance_score": 0.7,
                    "relevance_label": "relevant",
                    "sentiment_score": 0.1,
                    "sentiment_label": "neutral",
                    "has_risk_words": False,
                    "embedding": None,
                    "dedup_group_id": None,
                    "is_primary": True,
                    "processed_at": datetime.now(UTC),
                },
                {
                    "raw_post_id": 12,
                    "project_id": 3,
                    "relevance_score": 0.6,
                    "relevance_label": "relevant",
                    "sentiment_score": 0.1,
                    "sentiment_label": "neutral",
                    "has_risk_words": False,
                    "embedding": None,
                    "dedup_group_id": None,
                    "is_primary": True,
                    "processed_at": datetime.now(UTC),
                },
            ]
        )

        self.assertEqual(result["stored_count"], 1)
        self.assertEqual(len(result["sync_rows"]), 1)
        self.assertEqual(result["sync_rows"][0]["mention_id"], 202)
        self.assertEqual(result["sync_rows"][0]["author"], "author-2")
        update_query, update_params = fake_cursor.executed[2]
        self.assertIn("UPDATE raw_posts SET ml_processed = TRUE", update_query)
        self.assertEqual(update_params, ([12],))
        self.assertEqual(fake_connection.commits, 1)


class UpdateMentionResolvedCursor:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.executed: list[tuple[str, object]] = []
        self._fetchone_calls = 0
        self._updated_mention = {
            "id": 77,
            "raw_post_id": 900,
            "project_id": 3,
            "relevance_score": 0.91,
            "relevance_label": "relevant",
            "sentiment_score": 0.44,
            "sentiment_label": "negative",
            "has_risk_words": True,
            "dedup_group_id": None,
            "is_primary": True,
            "resolved": True,
            "processed_at": now,
            "source_id": 5,
            "source_type": "rss",
            "external_id": "rss-77",
            "url": "https://example.com/post-77",
            "title": "Mention title",
            "text": "Mention body",
            "author": "author",
            "published_at": now,
            "collected_at": now,
        }

    def execute(self, query: str, params=None) -> None:
        self.executed.append((" ".join(query.split()), params))

    def fetchone(self) -> dict | None:
        self._fetchone_calls += 1
        if self._fetchone_calls == 1:
            return {"id": 77}
        if self._fetchone_calls == 2:
            return dict(self._updated_mention)
        raise AssertionError("fetchone called unexpectedly")

    def __enter__(self) -> "UpdateMentionResolvedCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_update_mention_resolved_updates_flag_and_returns_mention() -> None:
    fake_cursor = UpdateMentionResolvedCursor()
    store = BrandRadarPostgresStore(Settings())
    store._connect = lambda *args, **kwargs: FakeConnection(fake_cursor)  # type: ignore[method-assign]

    result = store.update_mention_resolved(3, 77, resolved=True)

    assert result["id"] == 77
    assert result["project_id"] == 3
    assert result["resolved"] is True
    assert len(fake_cursor.executed) == 2

    update_query, update_params = fake_cursor.executed[0]
    select_query, select_params = fake_cursor.executed[1]

    assert "UPDATE mentions SET resolved = %s" in update_query
    assert update_params == (True, 77, 3)
    assert "m.resolved" in select_query
    assert select_params == (3, 77)
