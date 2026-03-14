from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings


@dataclass
class InMemoryStore:
    projects: dict[Any, Any] = field(default_factory=dict)
    brands: dict[Any, Any] = field(default_factory=dict)
    sources: dict[Any, Any] = field(default_factory=dict)
    mentions: dict[Any, Any] = field(default_factory=dict)
    alerts: dict[Any, Any] = field(default_factory=dict)
    events: dict[Any, Any] = field(default_factory=dict)
    statuses: dict[str, Any] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class DatabaseManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = InMemoryStore()
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._engine_error: str | None = None

        if settings.database_url:
            try:
                self._engine = create_async_engine(settings.database_url, future=True)
                self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)
            except Exception as exc:
                self._engine_error = str(exc)
                self._engine = None
                self._session_factory = None

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession] | None:
        return self._session_factory

    @property
    def using_in_memory_store(self) -> bool:
        return self._engine is None

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError("Database session factory is not configured")
        async with self._session_factory() as session:
            yield session

    async def ping(self) -> tuple[bool, str | None, int | None, dict[str, Any]]:
        if self._engine_error:
            return False, self._engine_error, None, {"mode": "configured_unavailable"}

        if self._engine is None:
            return True, None, None, {"mode": "in_memory"}

        started_at = perf_counter()
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            latency_ms = int((perf_counter() - started_at) * 1000)
            return True, None, latency_ms, {"mode": "async_sqlalchemy"}
        except Exception as exc:
            latency_ms = int((perf_counter() - started_at) * 1000)
            return False, str(exc), latency_ms, {"mode": "async_sqlalchemy"}

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
