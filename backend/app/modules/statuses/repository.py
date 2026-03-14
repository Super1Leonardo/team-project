from __future__ import annotations

from sqlalchemy import select

from app.infra.db.session import DatabaseManager
from app.modules.statuses.models import ComponentStatus


class ComponentStatusRepository:
    def __init__(self, database_manager: DatabaseManager) -> None:
        self.database_manager = database_manager

    async def upsert(self, status: ComponentStatus) -> ComponentStatus:
        if self.database_manager.using_in_memory_store:
            async with self.database_manager.store.lock:
                self.database_manager.store.statuses[status.component_name] = status
            return status

        async with self.database_manager.session() as session:
            existing = await session.scalar(
                select(ComponentStatus).where(ComponentStatus.component_name == status.component_name).limit(1)
            )
            if existing is None:
                session.add(status)
                await session.commit()
                await session.refresh(status)
                return status

            existing.component_type = status.component_type
            existing.status = status.status
            existing.latency_ms = status.latency_ms
            existing.last_seen_at = status.last_seen_at
            existing.last_error = status.last_error
            existing.meta = status.meta
            await session.commit()
            await session.refresh(existing)
            return existing

    async def list(self) -> list[ComponentStatus]:
        if self.database_manager.using_in_memory_store:
            return sorted(self.database_manager.store.statuses.values(), key=lambda item: item.component_name)

        async with self.database_manager.session() as session:
            result = await session.scalars(select(ComponentStatus).order_by(ComponentStatus.component_name.asc()))
            return list(result.all())
