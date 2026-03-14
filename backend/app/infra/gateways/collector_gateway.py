from __future__ import annotations

import uuid

import httpx

from app.core.config import Settings
from app.infra.gateways.health_gateway import ExternalHealthGateway
from app.ports.collector import CollectorPort, CollectorTriggerResult


class CollectorGateway(CollectorPort):
    def __init__(self, settings: Settings, health_gateway: ExternalHealthGateway) -> None:
        self.settings = settings
        self.health_gateway = health_gateway

    async def trigger(self, source_id: uuid.UUID) -> CollectorTriggerResult:
        if not self.settings.collector_service_url:
            return CollectorTriggerResult(
                accepted=True,
                provider="stub-collector",
                detail=f"Collection trigger accepted for source {source_id}",
            )

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.post(
                self.settings.collector_service_url.rstrip("/") + f"/trigger/{source_id}",
            )
            response.raise_for_status()
        return CollectorTriggerResult(
            accepted=True,
            provider="collector-service",
            detail=f"Collection trigger forwarded for source {source_id}",
        )

    async def healthcheck(self) -> tuple[bool, str | None, dict[str, object] | None]:
        if not self.settings.collector_service_url:
            return True, None, {"mode": "stub"}
        url = self.settings.collector_service_url.rstrip("/") + self.settings.collector_health_path
        ok, detail, latency_ms = await self.health_gateway.check_url(url)
        return ok, detail, {"mode": "external", "latency_ms": latency_ms}
