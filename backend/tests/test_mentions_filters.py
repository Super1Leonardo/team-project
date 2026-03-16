from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_brandradar_service
from backend.app.modules.brandradar.router import router as brandradar_router


def _build_mention() -> dict:
    now = datetime.now(UTC)
    return {
        "id": 1,
        "raw_post_id": 10,
        "project_id": 1,
        "source_id": 5,
        "source_type": "telegram",
        "external_id": "post-1",
        "url": "https://example.com/post-1",
        "title": "Example mention",
        "text": "Example mention body",
        "author": "tester",
        "published_at": now,
        "collected_at": now,
        "relevance_score": 0.91,
        "relevance_label": "relevant",
        "sentiment_score": 0.8,
        "sentiment_label": "negative",
        "has_risk_words": True,
        "dedup_group_id": None,
        "is_primary": True,
        "resolved": False,
        "top_tokens": [
            {
                "token": "Brand",
                "text": "Brand",
                "score": 0.87,
                "start": 0,
                "end": 5,
            }
        ],
        "highlight_spans": [
            {
                "text": "Brand",
                "score": 0.87,
                "start": 0,
                "end": 5,
            }
        ],
        "processed_at": now,
    }


class FakeBrandRadarService:
    def __init__(self):
        self.mention_calls: list[dict] = []
        self.cluster_calls: list[dict] = []
        self.default_feed_calls: list[dict] = []
        self.resolved_calls: list[dict] = []

    async def list_mentions(
        self,
        project_id: int,
        *,
        page: int = 1,
        page_size: int = 100,
        confidence_threshold: float | None = None,
        published_after: datetime | None = None,
        sentiment_label: str | None = None,
        primary_only: bool = False,
        relevant_only: bool = False,
        include_total: bool = True,
    ) -> dict:
        self.mention_calls.append(
            {
                "project_id": project_id,
                "page": page,
                "page_size": page_size,
                "confidence_threshold": confidence_threshold,
                "published_after": published_after,
                "sentiment_label": sentiment_label,
                "primary_only": primary_only,
                "relevant_only": relevant_only,
                "include_total": include_total,
            }
        )
        return {"items": [_build_mention()], "total": 1}

    async def list_default_mentions(
        self,
        *,
        page: int = 1,
        page_size: int = 100,
        confidence_threshold: float | None = None,
        published_after: datetime | None = None,
        sentiment_label: str | None = None,
        primary_only: bool = True,
        relevant_only: bool = True,
        include_total: bool = False,
    ) -> dict:
        self.default_feed_calls.append(
            {
                "page": page,
                "page_size": page_size,
                "confidence_threshold": confidence_threshold,
                "published_after": published_after,
                "sentiment_label": sentiment_label,
                "primary_only": primary_only,
                "relevant_only": relevant_only,
                "include_total": include_total,
            }
        )
        return {"items": [_build_mention()], "total": None}

    async def list_clusters(
        self,
        project_id: int,
        *,
        page: int = 1,
        page_size: int = 100,
        confidence_threshold: float | None = None,
        published_after: datetime | None = None,
        sentiment_label: str | None = None,
    ) -> dict:
        self.cluster_calls.append(
            {
                "project_id": project_id,
                "page": page,
                "page_size": page_size,
                "confidence_threshold": confidence_threshold,
                "published_after": published_after,
                "sentiment_label": sentiment_label,
            }
        )
        mention = _build_mention()
        return {
            "items": [
                {
                    "cluster_id": 7,
                    "dedup_group_id": 7,
                    "mentions_count": 3,
                    "first_seen_at": mention["published_at"],
                    "last_seen_at": mention["published_at"],
                    "representative_mention_id": mention["id"],
                    **mention,
                }
            ],
            "total": 1,
        }

    async def update_mention_resolved(
        self,
        project_id: int,
        mention_id: int,
        *,
        resolved: bool,
    ) -> dict:
        self.resolved_calls.append(
            {
                "project_id": project_id,
                "mention_id": mention_id,
                "resolved": resolved,
            }
        )
        mention = _build_mention()
        mention["id"] = mention_id
        mention["project_id"] = project_id
        mention["resolved"] = resolved
        return mention


def _build_client(service: FakeBrandRadarService) -> TestClient:
    app = FastAPI()
    app.include_router(brandradar_router, prefix="/api")
    app.dependency_overrides[get_brandradar_service] = lambda: service
    return TestClient(app)


def test_mentions_route_applies_confidence_period_and_pagination() -> None:
    service = FakeBrandRadarService()
    client = _build_client(service)

    response = client.get(
        "/api/projects/1/mentions",
        params={
            "page": 2,
            "page_size": 20,
            "confidence": "0.7",
            "period": "7d",
            "sentiment": "negative",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"] == {"total": 1, "page": 2, "page_size": 20}
    assert len(payload["data"]) == 1

    call = service.mention_calls[-1]
    assert call["project_id"] == 1
    assert call["page"] == 2
    assert call["page_size"] == 20
    assert call["confidence_threshold"] == 0.7
    assert call["sentiment_label"] == "negative"
    assert call["primary_only"] is False
    assert call["relevant_only"] is False
    assert call["include_total"] is True

    expected_lower_bound = datetime.now(UTC) - timedelta(days=7, seconds=5)
    expected_upper_bound = datetime.now(UTC) - timedelta(days=7) + timedelta(seconds=5)
    assert expected_lower_bound <= call["published_after"] <= expected_upper_bound


def test_mentions_route_accepts_limit_as_page_size_alias() -> None:
    service = FakeBrandRadarService()
    client = _build_client(service)

    response = client.get(
        "/api/projects/1/mentions",
        params={"limit": 15},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"] == {"total": 1, "page": 1, "page_size": 15}

    call = service.mention_calls[-1]
    assert call["page"] == 1
    assert call["page_size"] == 15
    assert call["confidence_threshold"] is None
    assert call["published_after"] is None
    assert call["sentiment_label"] is None
    assert call["primary_only"] is False
    assert call["relevant_only"] is False
    assert call["include_total"] is True


def test_mentions_route_passes_fast_path_flags() -> None:
    service = FakeBrandRadarService()
    client = _build_client(service)

    response = client.get(
        "/api/projects/1/mentions",
        params={
            "limit": 50,
            "primary_only": "true",
            "relevant_only": "true",
            "include_total": "false",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"] == {"total": None, "page": 1, "page_size": 50}

    call = service.mention_calls[-1]
    assert call["primary_only"] is True
    assert call["relevant_only"] is True
    assert call["include_total"] is False


def test_feed_route_uses_default_fast_flags() -> None:
    service = FakeBrandRadarService()
    client = _build_client(service)

    response = client.get(
        "/api/feed",
        params={
            "limit": 50,
            "confidence": "0.7",
            "period": "7d",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"] == {"total": None, "page": 1, "page_size": 50}
    assert len(payload["data"]) == 1

    call = service.default_feed_calls[-1]
    assert call["page"] == 1
    assert call["page_size"] == 50
    assert call["confidence_threshold"] == 0.7
    assert call["primary_only"] is True
    assert call["relevant_only"] is True
    assert call["include_total"] is False


def test_clusters_route_applies_filters_and_limit_alias() -> None:
    service = FakeBrandRadarService()
    client = _build_client(service)

    response = client.get(
        "/api/projects/1/clusters",
        params={
            "page": 3,
            "limit": 25,
            "confidence": "0.5",
            "period": "30d",
            "sentiment": "negative",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"] == {"total": 1, "page": 3, "page_size": 25}
    assert payload["data"][0]["cluster_id"] == 7
    assert payload["data"][0]["mentions_count"] == 3

    call = service.cluster_calls[-1]
    assert call["project_id"] == 1
    assert call["page"] == 3
    assert call["page_size"] == 25
    assert call["confidence_threshold"] == 0.5
    assert call["sentiment_label"] == "negative"

    expected_lower_bound = datetime.now(UTC) - timedelta(days=30, seconds=5)
    expected_upper_bound = datetime.now(UTC) - timedelta(days=30) + timedelta(seconds=5)
    assert expected_lower_bound <= call["published_after"] <= expected_upper_bound


def test_update_mention_resolved_route_updates_single_mention() -> None:
    service = FakeBrandRadarService()
    client = _build_client(service)

    response = client.post(
        "/api/projects/3/mentions/77/resolved",
        json={"resolved": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["id"] == 77
    assert payload["data"]["project_id"] == 3
    assert payload["data"]["resolved"] is True

    assert service.resolved_calls == [
        {
            "project_id": 3,
            "mention_id": 77,
            "resolved": True,
        }
    ]
