from __future__ import annotations

import uuid

import pytest


async def bootstrap_entities(client, *, threshold: int = 2, exceptions: list[str] | None = None):
    project_name = f"Project-{uuid.uuid4()}"
    project = (
        await client.post(
            "/projects",
            json={"name": project_name, "description": "test project"},
        )
    ).json()
    brand = (
        await client.post(
            "/brands",
            json={
                "project_id": project["id"],
                "name": "Acme",
                "keywords": ["Acme"],
                "exceptions": exceptions or [],
                "risk_words": ["сбой", "утечка"],
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
                "name": f"Web-{uuid.uuid4()}",
                "type": "web",
                "config": {"base_url": "https://example.com"},
                "is_active": True,
            },
        )
    ).json()
    return project, brand, source


@pytest.mark.asyncio
async def test_health_and_statuses_endpoints_respond(client) -> None:
    health_response = await client.get("/health")
    statuses_response = await client.get("/statuses")

    assert health_response.status_code == 200
    assert statuses_response.status_code == 200

    health_payload = health_response.json()
    component_names = {component["component_name"] for component in health_payload["components"]}
    assert {"api", "db", "redis", "ml_gateway", "collector_gateway"}.issubset(component_names)
    assert statuses_response.json()


@pytest.mark.asyncio
async def test_ingestion_happy_path_duplicate_and_filters(client) -> None:
    _, _, source = await bootstrap_entities(client, threshold=3)

    ingest_response = await client.post(
        "/internal/mentions/ingest",
        json={
            "source_id": source["id"],
            "title": "У Acme произошел сбой в сервисе",
            "text": "Клиенты пишут, что у Acme произошел серьезный сбой сервиса.",
            "raw_url": "https://example.com/posts/1",
            "created_at": "2026-03-14T09:10:00Z",
            "metadata": {"site": "example.com"},
        },
    )

    assert ingest_response.status_code == 201
    mention = ingest_response.json()
    assert mention["source"]["id"] == source["id"]
    assert mention["raw_url"] == "https://example.com/posts/1"
    assert mention["ml_data"]["relevance"] == "relevant"
    assert mention["ml_data"]["sentiment"] == "negative"
    assert mention["ml_data"]["criticality"] in {"high", "critical", "medium"}

    duplicate_response = await client.post(
        "/internal/mentions/ingest",
        json={
            "source_id": source["id"],
            "title": "Повтор новости про Acme",
            "text": "Формально другой текст, но URL тот же.",
            "raw_url": "https://example.com/posts/1#duplicate",
            "created_at": "2026-03-14T09:11:00Z",
            "metadata": {"site": "example.com"},
        },
    )

    assert duplicate_response.status_code == 201
    duplicate_mention = duplicate_response.json()
    assert duplicate_mention["is_duplicate"] is True
    assert duplicate_mention["is_duplicate_of"] == mention["id"]

    mentions_response = await client.get(
        "/mentions",
        params={
            "source_id": source["id"],
            "source_type": "web",
            "relevance": "relevant",
            "duplicates": "exclude",
            "limit": 20,
            "offset": 0,
        },
    )
    assert mentions_response.status_code == 200
    mentions_payload = mentions_response.json()
    assert mentions_payload["total"] == 1
    assert mentions_payload["items"][0]["id"] == mention["id"]

    duplicates_only_response = await client.get("/mentions", params={"duplicates": "only"})
    assert duplicates_only_response.status_code == 200
    assert duplicates_only_response.json()["total"] == 1

    analytics_response = await client.get("/analytics/mentions-chart", params={"relevance": "relevant"})
    assert analytics_response.status_code == 200
    assert analytics_response.json()["totals"]["total"] >= 1


@pytest.mark.asyncio
async def test_irrelevant_mention_does_not_create_alert(client) -> None:
    _, _, source = await bootstrap_entities(client, threshold=1, exceptions=["acme junior"])

    ingest_response = await client.post(
        "/internal/mentions/ingest",
        json={
            "source_id": source["id"],
            "title": "Acme Junior снова в центре скандала",
            "text": "У Acme Junior случился сбой, но это исключение бренда.",
            "raw_url": "https://example.com/posts/irrelevant",
            "created_at": "2026-03-14T09:20:00Z",
        },
    )

    assert ingest_response.status_code == 201
    mention = ingest_response.json()
    assert mention["ml_data"]["relevance"] == "irrelevant"

    alerts_response = await client.get("/alerts")
    assert alerts_response.status_code == 200
    assert alerts_response.json() == []


@pytest.mark.asyncio
async def test_negative_relevant_mentions_create_alert_and_cooldown_blocks_repeat(client) -> None:
    _, brand, source = await bootstrap_entities(client, threshold=2)

    payloads = [
        {
            "source_id": source["id"],
            "title": "Acme: крупный сбой",
            "text": "У Acme произошел сбой и жалобы растут.",
            "raw_url": "https://example.com/posts/100",
            "created_at": "2026-03-14T09:30:00Z",
        },
        {
            "source_id": source["id"],
            "title": "Acme снова падает",
            "text": "Еще один негативный сигнал: сервис Acme упал.",
            "raw_url": "https://example.com/posts/101",
            "created_at": "2026-03-14T09:31:00Z",
        },
        {
            "source_id": source["id"],
            "title": "Acme продолжает сбоить",
            "text": "Третий негативный пост про Acme и новый сбой.",
            "raw_url": "https://example.com/posts/102",
            "created_at": "2026-03-14T09:32:00Z",
        },
    ]

    for payload in payloads:
        response = await client.post("/internal/mentions/ingest", json=payload)
        assert response.status_code == 201

    alerts_response = await client.get("/alerts", params={"brand_id": brand["id"]})
    assert alerts_response.status_code == 200
    alerts = alerts_response.json()
    assert len(alerts) == 1
    assert alerts[0]["type"] == "spike_negative"

    events_response = await client.get("/events", params={"event_type": "alert_created"})
    assert events_response.status_code == 200
    assert events_response.json()["total"] == 1
