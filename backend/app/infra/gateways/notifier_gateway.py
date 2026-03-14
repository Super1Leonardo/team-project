from __future__ import annotations

import httpx

from app.core.config import Settings
from app.infra.gateways.health_gateway import ExternalHealthGateway
from app.ports.notifier import NotificationPayload, NotificationResult, NotifierPort


class NotifierGateway(NotifierPort):
    def __init__(self, settings: Settings, health_gateway: ExternalHealthGateway) -> None:
        self.settings = settings
        self.health_gateway = health_gateway

    async def send(self, payload: NotificationPayload) -> NotificationResult:
        if not self.settings.notifier_webhook_url:
            return NotificationResult(
                delivered=True,
                provider="stub-notifier",
                detail=f"Stub notification for alert {payload.alert_id}",
            )

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.post(
                self.settings.notifier_webhook_url,
                json={
                    "alert_id": str(payload.alert_id),
                    "project_id": str(payload.project_id),
                    "brand_id": str(payload.brand_id),
                    "brand_name": payload.brand_name,
                    "alert_type": payload.alert_type,
                    "mentions_count": payload.mentions_count,
                    "payload": payload.payload,
                },
            )
            response.raise_for_status()
        return NotificationResult(delivered=True, provider="webhook", detail="Webhook delivered")

    async def healthcheck(self) -> tuple[bool, str | None, dict[str, object] | None]:
        if not self.settings.notifier_webhook_url:
            return True, None, {"mode": "stub"}
        ok, detail, latency_ms = await self.health_gateway.check_url(self.settings.notifier_webhook_url)
        return ok, detail, {"mode": "webhook", "latency_ms": latency_ms}
