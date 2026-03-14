from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.infra.db.session import DatabaseManager
from app.modules.brands.models import Brand


class BrandRepository:
    def __init__(self, database_manager: DatabaseManager) -> None:
        self.database_manager = database_manager

    async def list(self, project_id: uuid.UUID | None = None) -> list[Brand]:
        if self.database_manager.using_in_memory_store:
            items = list(self.database_manager.store.brands.values())
            if project_id is not None:
                items = [brand for brand in items if brand.project_id == project_id]
            return sorted(items, key=lambda item: (item.updated_at, item.name), reverse=True)

        statement = select(Brand)
        if project_id is not None:
            statement = statement.where(Brand.project_id == project_id)
        statement = statement.order_by(Brand.updated_at.desc(), Brand.name.desc())

        async with self.database_manager.session() as session:
            result = await session.scalars(statement)
            return list(result.all())

    async def list_by_project(self, project_id: uuid.UUID) -> list[Brand]:
        return await self.list(project_id=project_id)

    async def get(self, brand_id: uuid.UUID) -> Brand | None:
        if self.database_manager.using_in_memory_store:
            return self.database_manager.store.brands.get(brand_id)

        async with self.database_manager.session() as session:
            return await session.get(Brand, brand_id)

    async def get_by_name(self, project_id: uuid.UUID, name: str) -> Brand | None:
        if self.database_manager.using_in_memory_store:
            lowered = name.casefold()
            return next(
                (
                    brand
                    for brand in self.database_manager.store.brands.values()
                    if brand.project_id == project_id and brand.name.casefold() == lowered
                ),
                None,
            )

        lowered = name.casefold()
        async with self.database_manager.session() as session:
            return await session.scalar(
                select(Brand).where(
                    Brand.project_id == project_id,
                    func.lower(Brand.name) == lowered,
                )
            )

    async def add(self, brand: Brand) -> Brand:
        if self.database_manager.using_in_memory_store:
            async with self.database_manager.store.lock:
                self.database_manager.store.brands[brand.id] = brand
            return brand

        async with self.database_manager.session() as session:
            session.add(brand)
            await session.commit()
            await session.refresh(brand)
            return brand

    async def update(self, brand: Brand) -> Brand:
        if self.database_manager.using_in_memory_store:
            async with self.database_manager.store.lock:
                self.database_manager.store.brands[brand.id] = brand
            return brand

        async with self.database_manager.session() as session:
            merged = await session.merge(brand)
            await session.commit()
            await session.refresh(merged)
            return merged
