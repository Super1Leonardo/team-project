from __future__ import annotations

from time import perf_counter

import httpx


class ExternalHealthGateway:
    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds

    async def check_url(self, url: str) -> tuple[bool, str | None, int | None]:
        started_at = perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url)
            latency_ms = int((perf_counter() - started_at) * 1000)
            if response.status_code >= 400:
                return False, f"HTTP {response.status_code}", latency_ms
            return True, None, latency_ms
        except Exception as exc:
            latency_ms = int((perf_counter() - started_at) * 1000)
            return False, str(exc), latency_ms
