from __future__ import annotations

import uuid

from app.infra.db.session import InMemoryStore
from app.modules.brands.models import Brand


class BrandRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    async def list(self, project_id: uuid.UUID | None = None) -> list[Brand]:
        items = list(self.store.brands.values())
        if project_id is not None:
            items = [brand for brand in items if brand.project_id == project_id]
        return sorted(items, key=lambda item: (item.updated_at, item.name), reverse=True)

    async def list_by_project(self, project_id: uuid.UUID) -> list[Brand]:
        return await self.list(project_id=project_id)

    async def get(self, brand_id: uuid.UUID) -> Brand | None:
        return self.store.brands.get(brand_id)

    async def get_by_name(self, project_id: uuid.UUID, name: str) -> Brand | None:
        lowered = name.casefold()
        return next(
            (
                brand
                for brand in self.store.brands.values()
                if brand.project_id == project_id and brand.name.casefold() == lowered
            ),
            None,
        )

    async def add(self, brand: Brand) -> Brand:
        async with self.store.lock:
            self.store.brands[brand.id] = brand
        return brand

    async def update(self, brand: Brand) -> Brand:
        async with self.store.lock:
            self.store.brands[brand.id] = brand
        return brand
