from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.config import Settings
from app.infra.db.base import Base
from app.main import create_app


@pytest.fixture
def app():
    return create_app(
        Settings(
            database_url=None,
            redis_url=None,
            ml_service_url=None,
            collector_service_url=None,
            notifier_webhook_url=None,
        )
    )


@pytest.fixture
def container(app):
    return app.state.container


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
    await app.state.container.shutdown()


@pytest.fixture
def postgres_database_url() -> str:
    database_url = os.getenv("BRANDRADAR_DATABASE_URL")
    if not database_url:
        pytest.skip("Postgres tests require BRANDRADAR_DATABASE_URL to be set")
    return database_url


async def _prepare_postgres_database(app) -> None:
    database_manager = app.state.container.database_manager
    engine = database_manager._engine
    if engine is None:
        pytest.skip("Postgres engine is not configured")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.execute(
            text(
                "TRUNCATE TABLE component_statuses, event_logs, alerts, mentions, sources, brands, projects CASCADE"
            )
        )


@pytest_asyncio.fixture
async def postgres_app(postgres_database_url: str):
    app = create_app(
        Settings(
            database_url=postgres_database_url,
            redis_url=None,
            ml_service_url=None,
            collector_service_url=None,
            notifier_webhook_url=None,
        )
    )
    await _prepare_postgres_database(app)
    yield app
    await app.state.container.shutdown()


@pytest_asyncio.fixture
async def postgres_client(postgres_app):
    transport = ASGITransport(app=postgres_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
