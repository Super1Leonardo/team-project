from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


async def bootstrap_postgres_entities(client, *, threshold: int = 2):
    suffix = str(uuid.uuid4())[:8]
    project = (
        await client.post(
            "/projects",
            json={"name": f"PG Project {suffix}", "description": "postgres integration"},
        )
    ).json()
    brand = (
        await client.post(
            "/brands",
            json={
                "project_id": project["id"],
                "name": f"Acme-{suffix}",
                "keywords": [f"Acme-{suffix}", "Acme"],
                "exceptions": ["Acme Junior"],
                "risk_words": ["сбой", "утечка", "жалоба"],
                "spike_threshold": threshold,
                "spike_window_minutes": 60,
                "spike_cooldown_minutes": 120,
            },
        )
    ).json()
    source = (
        await client.post(
            "/sources",
            json={
                "project_id": project["id"],
                "name": f"Web-{suffix}",
                "type": "web",
                "config": {"base_url": "https://example.com"},
                "is_active": True,
            },
        )
    ).json()
    return project, brand, source


@pytest.mark.asyncio
async def test_postgres_project_persists_across_app_restart(postgres_database_url: str, postgres_client) -> None:
    project_name = f"Persist-{uuid.uuid4()}"
    create_response = await postgres_client.post(
        "/projects",
        json={"name": project_name, "description": "persist across restart"},
    )
    assert create_response.status_code == 201
    created_project = create_response.json()

    restarted_app = create_app(
        Settings(
            database_url=postgres_database_url,
            redis_url=None,
            ml_service_url=None,
            collector_service_url=None,
            notifier_webhook_url=None,
        )
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=restarted_app), base_url="http://testserver") as client:
            list_response = await client.get("/projects")
            assert list_response.status_code == 200
            projects = list_response.json()
            assert any(project["id"] == created_project["id"] for project in projects)
    finally:
        await restarted_app.state.container.shutdown()


@pytest.mark.asyncio
async def test_postgres_ingestion_alerts_events_and_analytics(postgres_client) -> None:
    _, brand, source = await bootstrap_postgres_entities(postgres_client, threshold=2)

    payloads = [
        {
            "source_id": source["id"],
            "title": f"У {brand['name']} произошел сбой",
            "text": f"Пользователи пишут, что у {brand['name']} произошел серьезный сбой сервиса.",
            "raw_url": f"https://example.com/{uuid.uuid4()}/1",
            "created_at": "2026-03-14T09:10:00Z",
            "metadata": {"site": "example.com"},
        },
        {
            "source_id": source["id"],
            "title": f"{brand['name']} снова падает",
            "text": f"Еще один негативный пост: сервис {brand['name']} упал.",
            "raw_url": f"https://example.com/{uuid.uuid4()}/2",
            "created_at": "2026-03-14T09:11:00Z",
            "metadata": {"site": "example.com"},
        },
    ]

    responses = []
    for payload in payloads:
        response = await postgres_client.post("/internal/mentions/ingest", json=payload)
        assert response.status_code == 201
        responses.append(response.json())

    assert responses[0]["is_duplicate"] is False
    assert responses[1]["is_duplicate"] is False
    assert responses[0]["ml_data"]["sentiment"] == "negative"
    assert responses[1]["ml_data"]["sentiment"] == "negative"

    duplicate_response = await postgres_client.post(
        "/internal/mentions/ingest",
        json={
            "source_id": source["id"],
            "title": "Повтор публикации",
            "text": "Другой текст, но та же ссылка.",
            "raw_url": payloads[0]["raw_url"] + "#dup",
            "created_at": "2026-03-14T09:12:00Z",
            "metadata": {"site": "example.com"},
        },
    )
    assert duplicate_response.status_code == 201
    duplicate_payload = duplicate_response.json()
    assert duplicate_payload["is_duplicate"] is True
    assert duplicate_payload["is_duplicate_of"] == responses[0]["id"]

    mentions_response = await postgres_client.get(
        "/mentions",
        params={"source_id": source["id"], "duplicates": "exclude", "limit": 20, "offset": 0},
    )
    assert mentions_response.status_code == 200
    mentions_payload = mentions_response.json()
    assert mentions_payload["total"] == 2

    alerts_response = await postgres_client.get("/alerts", params={"brand_id": brand["id"]})
    assert alerts_response.status_code == 200
    alerts = alerts_response.json()
    assert len(alerts) == 1
    assert alerts[0]["type"] == "spike_negative"

    events_response = await postgres_client.get("/events", params={"limit": 200})
    assert events_response.status_code == 200
    event_types = {item["event_type"] for item in events_response.json()["items"]}
    assert "mention_ingested" in event_types
    assert "duplicate_detected" in event_types
    assert "alert_created" in event_types
    assert "notification_sent" in event_types

    analytics_response = await postgres_client.get(
        "/analytics/mentions-chart",
        params={"brand_id": brand["id"], "relevance": "relevant"},
    )
    assert analytics_response.status_code == 200
    analytics_payload = analytics_response.json()
    assert analytics_payload["totals"]["total"] == 2


@pytest.mark.asyncio
async def test_postgres_health_and_statuses_endpoints(postgres_client) -> None:
    health_response = await postgres_client.get("/health")
    statuses_response = await postgres_client.get("/statuses")

    assert health_response.status_code == 200
    assert statuses_response.status_code == 200

    health_payload = health_response.json()
    component_names = {component["component_name"] for component in health_payload["components"]}
    assert {"api", "db", "redis", "ml_gateway", "collector_gateway"}.issubset(component_names)

    statuses_payload = statuses_response.json()
    assert {item["component_name"] for item in statuses_payload}.issuperset(component_names)
