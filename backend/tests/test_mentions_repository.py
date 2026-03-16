from __future__ import annotations

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

    count_query, count_params = fake_cursor.executed[0]
    data_query, data_params = fake_cursor.executed[1]

    assert "COUNT(*) AS total" in count_query
    assert "m.relevance_score >= %s" in count_query
    assert "rp.published_at >= %s" in count_query
    assert "m.sentiment_label = %s" in count_query
    assert count_params == [3, 0.7, published_after, "negative"]

    assert "LIMIT %s" in data_query
    assert "OFFSET %s" in data_query
    assert "m.sentiment_label = %s" in data_query
    assert data_params == [3, 0.7, published_after, "negative", 20, 20]
