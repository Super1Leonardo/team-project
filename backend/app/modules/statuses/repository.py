from __future__ import annotations

from app.infra.db.session import InMemoryStore
from app.modules.statuses.models import ComponentStatus


class ComponentStatusRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    async def upsert(self, status: ComponentStatus) -> ComponentStatus:
        async with self.store.lock:
            self.store.statuses[status.component_name] = status
        return status

    async def list(self) -> list[ComponentStatus]:
        return sorted(self.store.statuses.values(), key=lambda item: item.component_name)
