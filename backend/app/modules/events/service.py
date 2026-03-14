from __future__ import annotations

import uuid

from app.common.enums import EventLevel
from app.core.time import utc_now
from app.modules.events.models import EventLog
from app.modules.events.repository import EventLogRepository


class EventLogService:
    def __init__(self, repository: EventLogRepository) -> None:
        self.repository = repository

    async def record(
        self,
        event_type: str,
        entity_type: str,
        *,
        entity_id: uuid.UUID | None = None,
        level: EventLevel = EventLevel.INFO,
        payload: dict | None = None,
    ) -> EventLog:
        event = EventLog(
            id=uuid.uuid4(),
            event_type=event_type,
            level=level,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
            created_at=utc_now(),
        )
        return await self.repository.add(event)

    async def list(
        self,
        *,
        event_type: str | None = None,
        level: EventLevel | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[EventLog], int]:
        return await self.repository.list(event_type=event_type, level=level, limit=limit, offset=offset)
