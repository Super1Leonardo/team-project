from __future__ import annotations

from sqlalchemy import func, select

from app.common.enums import EventLevel
from app.infra.db.session import DatabaseManager
from app.modules.events.models import EventLog


class EventLogRepository:
    def __init__(self, database_manager: DatabaseManager) -> None:
        self.database_manager = database_manager

    async def add(self, event: EventLog) -> EventLog:
        if self.database_manager.using_in_memory_store:
            async with self.database_manager.store.lock:
                self.database_manager.store.events[event.id] = event
            return event

        async with self.database_manager.session() as session:
            session.add(event)
            await session.commit()
            await session.refresh(event)
            return event

    async def list(
        self,
        event_type: str | None = None,
        level: EventLevel | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[EventLog], int]:
        if self.database_manager.using_in_memory_store:
            items = list(self.database_manager.store.events.values())
            if event_type is not None:
                items = [event for event in items if event.event_type == event_type]
            if level is not None:
                items = [event for event in items if event.level == level]
            items = sorted(items, key=lambda item: item.created_at, reverse=True)
            total = len(items)
            return items[offset : offset + limit], total

        statement = select(EventLog)
        count_statement = select(func.count()).select_from(EventLog)
        if event_type is not None:
            statement = statement.where(EventLog.event_type == event_type)
            count_statement = count_statement.where(EventLog.event_type == event_type)
        if level is not None:
            statement = statement.where(EventLog.level == level)
            count_statement = count_statement.where(EventLog.level == level)
        statement = statement.order_by(EventLog.created_at.desc()).offset(offset).limit(limit)

        async with self.database_manager.session() as session:
            items = list((await session.scalars(statement)).all())
            total = int((await session.scalar(count_statement)) or 0)
            return items, total
