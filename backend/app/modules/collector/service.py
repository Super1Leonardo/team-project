from __future__ import annotations

import uuid

from app.common.enums import EventLevel
from app.core.constants import EVENT_SOURCE_FAILED
from app.core.exceptions import NotFoundError, ValidationError
from app.core.time import utc_now
from app.modules.events.service import EventLogService
from app.modules.sources.repository import SourceRepository
from app.ports.collector import CollectorPort, CollectorTriggerResult


class CollectorService:
    def __init__(
        self,
        source_repository: SourceRepository,
        collector_gateway: CollectorPort,
        event_log_service: EventLogService,
    ) -> None:
        self.source_repository = source_repository
        self.collector_gateway = collector_gateway
        self.event_log_service = event_log_service

    async def trigger(self, source_id: uuid.UUID) -> CollectorTriggerResult:
        source = await self.source_repository.get(source_id)
        if source is None:
            raise NotFoundError(f"Source '{source_id}' not found")
        if not source.is_active:
            raise ValidationError(f"Source '{source.name}' is inactive")

        try:
            result = await self.collector_gateway.trigger(source_id)
            source.last_collected_at = utc_now()
            source.last_error_at = None
            await self.source_repository.update(source)
            return result
        except Exception as exc:
            source.last_error_at = utc_now()
            await self.source_repository.update(source)
            await self.event_log_service.record(
                EVENT_SOURCE_FAILED,
                "source",
                entity_id=source.id,
                level=EventLevel.ERROR,
                payload={"detail": str(exc)},
            )
            raise
