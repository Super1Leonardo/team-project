from __future__ import annotations

from app.common.enums import EventLevel
from app.infra.db.session import InMemoryStore
from app.modules.events.models import EventLog


class EventLogRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    async def add(self, event: EventLog) -> EventLog:
        async with self.store.lock:
            self.store.events[event.id] = event
        return event

    async def list(
        self,
        event_type: str | None = None,
        level: EventLevel | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[EventLog], int]:
        items = list(self.store.events.values())
        if event_type is not None:
            items = [event for event in items if event.event_type == event_type]
        if level is not None:
            items = [event for event in items if event.level == level]
        items = sorted(items, key=lambda item: item.created_at, reverse=True)
        total = len(items)
        return items[offset : offset + limit], total
