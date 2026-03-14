from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from app.core.config import Settings
from app.core.time import utc_now


@dataclass
class _RedisEntry:
    value: Any
    expires_at: object | None = None


class InMemoryRedis:
    def __init__(self) -> None:
        self._data: dict[str, _RedisEntry] = {}
        self._lock = asyncio.Lock()

    def _is_expired(self, key: str) -> bool:
        entry = self._data.get(key)
        if entry is None or entry.expires_at is None:
            return False
        if entry.expires_at <= utc_now():
            self._data.pop(key, None)
            return True
        return False

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> Any:
        async with self._lock:
            if self._is_expired(key):
                return None
            entry = self._data.get(key)
            return None if entry is None else entry.value

    async def set(self, key: str, value: Any, ex: int | None = None, nx: bool = False) -> bool:
        async with self._lock:
            self._is_expired(key)
            if nx and key in self._data:
                return False
            expires_at = utc_now() + timedelta(seconds=ex) if ex else None
            self._data[key] = _RedisEntry(value=value, expires_at=expires_at)
            return True

    async def incr(self, key: str) -> int:
        async with self._lock:
            current_value = 0
            if not self._is_expired(key) and key in self._data:
                current_value = int(self._data[key].value)
            expires_at = self._data[key].expires_at if key in self._data else None
            next_value = current_value + 1
            self._data[key] = _RedisEntry(value=next_value, expires_at=expires_at)
            return next_value

    async def expire(self, key: str, seconds: int) -> bool:
        async with self._lock:
            if self._is_expired(key) or key not in self._data:
                return False
            self._data[key].expires_at = utc_now() + timedelta(seconds=seconds)
            return True

    async def exists(self, key: str) -> bool:
        async with self._lock:
            return not self._is_expired(key) and key in self._data

    async def ttl(self, key: str) -> int | None:
        async with self._lock:
            if self._is_expired(key) or key not in self._data:
                return None
            expires_at = self._data[key].expires_at
            if expires_at is None:
                return None
            return max(int((expires_at - utc_now()).total_seconds()), 0)

    async def delete(self, key: str) -> int:
        async with self._lock:
            existed = key in self._data
            self._data.pop(key, None)
            return 1 if existed else 0

    async def close(self) -> None:
        return None


class RedisClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._mode = "in_memory"
        self._client: Any = InMemoryRedis()
        self._init_error: str | None = None

        if settings.redis_url:
            try:
                import redis.asyncio as redis_async  # type: ignore

                self._client = redis_async.from_url(settings.redis_url, decode_responses=True)
                self._mode = "redis"
            except Exception as exc:
                self._init_error = str(exc)
                self._client = InMemoryRedis()
                self._mode = "in_memory_fallback"

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def init_error(self) -> str | None:
        return self._init_error

    async def ping(self) -> bool:
        return bool(await self._client.ping())

    async def get(self, key: str) -> Any:
        return await self._client.get(key)

    async def set(self, key: str, value: Any, ex: int | None = None, nx: bool = False) -> bool:
        return bool(await self._client.set(key, value, ex=ex, nx=nx))

    async def incr(self, key: str) -> int:
        return int(await self._client.incr(key))

    async def expire(self, key: str, seconds: int) -> bool:
        return bool(await self._client.expire(key, seconds))

    async def exists(self, key: str) -> bool:
        return bool(await self._client.exists(key))

    async def ttl(self, key: str) -> int | None:
        if hasattr(self._client, "ttl"):
            result = await self._client.ttl(key)
            if result in (-2, -1, None):
                return None
            return int(result)
        return None

    async def delete(self, key: str) -> int:
        return int(await self._client.delete(key))

    async def close(self) -> None:
        close_method = getattr(self._client, "close", None)
        if close_method is None:
            return
        result = close_method()
        if asyncio.iscoroutine(result):
            await result


def build_redis_client(settings: Settings) -> RedisClient:
    return RedisClient(settings)
