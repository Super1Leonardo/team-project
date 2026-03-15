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
        "processed_at": now,
    }


class FakeBrandRadarService:
    def __init__(self):
        self.calls: list[dict] = []

    async def list_mentions(
        self,
        project_id: int,
        *,
        page: int = 1,
        page_size: int = 100,
        confidence_threshold: float | None = None,
        published_after: datetime | None = None,
    ) -> dict:
        self.calls.append(
            {
                "project_id": project_id,
                "page": page,
                "page_size": page_size,
                "confidence_threshold": confidence_threshold,
                "published_after": published_after,
            }
        )
        return {"items": [_build_mention()], "total": 1}


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
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meta"] == {"total": 1, "page": 2, "page_size": 20}
    assert len(payload["data"]) == 1

    call = service.calls[-1]
    assert call["project_id"] == 1
    assert call["page"] == 2
    assert call["page_size"] == 20
    assert call["confidence_threshold"] == 0.7

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

    call = service.calls[-1]
    assert call["page"] == 1
    assert call["page_size"] == 15
    assert call["confidence_threshold"] is None
    assert call["published_after"] is None
