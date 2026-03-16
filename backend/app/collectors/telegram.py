from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.app.collectors.base import BaseCollector
from backend.app.core.exceptions import DomainValidationError
from backend.app.infra.gateways.telegram_gateway import TelegramGateway, TelegramServiceError


class TelegramCollector(BaseCollector):
    source_type = "telegram"

    def __init__(self, gateway: TelegramGateway):
        self.gateway = gateway

    async def collect(
        self,
        source: dict[str, Any],
        *,
        published_after: datetime | None = None,
    ):
        source_config = source.get("source_config") or {}
        channel = source_config.get("channel")
        if not channel:
            raise DomainValidationError(
                f"Telegram source {source['id']} must contain source_config.channel."
            )

        response = await self.gateway.parse_configured_channels(
            published_after=published_after,
            channels=[channel],
        )
        errors = [
            result.error
            for result in response.results
            if result.status != "ok" and result.error
        ]
        if errors and not response.items:
            raise TelegramServiceError("; ".join(errors))

        return response.items
