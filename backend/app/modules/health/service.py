from __future__ import annotations

from typing import Any

from backend.app.core.config import Settings
from backend.app.infra.db.clickhouse import ClickHouseMentionEventsStore
from backend.app.infra.db.postgres import BrandRadarPostgresStore
from backend.app.modules.messages.repository import MessagesRepository


class HealthService:
    def __init__(
        self,
        *,
        settings: Settings,
        postgres_store: BrandRadarPostgresStore,
        raw_messages_store: MessagesRepository,
        mention_events_store: ClickHouseMentionEventsStore,
    ):
        self.settings = settings
        self.postgres_store = postgres_store
        self.raw_messages_store = raw_messages_store
        self.mention_events_store = mention_events_store

    def healthcheck(self) -> dict[str, Any]:
        postgres_status = self._probe(self.postgres_store.ping)
        raw_messages_status = self._probe(self.raw_messages_store.ping)
        mention_events_status = self._probe(self.mention_events_store.ping)

        unhealthy_count = sum(
            status == "unhealthy"
            for status in (
                postgres_status,
                raw_messages_status,
                mention_events_status,
            )
        )
        if unhealthy_count == 0:
            overall_status = "healthy"
        elif unhealthy_count == 3:
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"

        return {
            "status": overall_status,
            "postgres": postgres_status,
            "clickhouse_raw_messages": raw_messages_status,
            "clickhouse_mention_events": mention_events_status,
            "telegram_credentials_configured": self.settings.credentials_configured,
            "external_ml_url": self.settings.external_ml_base_url,
        }

    @staticmethod
    def _probe(callback) -> str:
        try:
            callback()
        except Exception:
            return "unhealthy"
        return "healthy"
