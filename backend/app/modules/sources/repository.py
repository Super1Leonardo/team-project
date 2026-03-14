from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.infra.db.session import DatabaseManager
from app.modules.sources.models import Source


class SourceRepository:
    def __init__(self, database_manager: DatabaseManager) -> None:
        self.database_manager = database_manager

    async def list(self, project_id: uuid.UUID | None = None) -> list[Source]:
        if self.database_manager.using_in_memory_store:
            items = list(self.database_manager.store.sources.values())
            if project_id is not None:
                items = [source for source in items if source.project_id == project_id]
            return sorted(items, key=lambda item: item.created_at, reverse=True)

        statement = select(Source)
        if project_id is not None:
            statement = statement.where(Source.project_id == project_id)
        statement = statement.order_by(Source.created_at.desc())

        async with self.database_manager.session() as session:
            result = await session.scalars(statement)
            return list(result.all())

    async def get(self, source_id: uuid.UUID) -> Source | None:
        if self.database_manager.using_in_memory_store:
            return self.database_manager.store.sources.get(source_id)

        async with self.database_manager.session() as session:
            return await session.get(Source, source_id)

    async def get_by_identifier(self, identifier: uuid.UUID | str) -> Source | None:
        if self.database_manager.using_in_memory_store:
            if isinstance(identifier, uuid.UUID):
                return await self.get(identifier)

            try:
                parsed = uuid.UUID(str(identifier))
            except (TypeError, ValueError):
                parsed = None

            if parsed is not None and parsed in self.database_manager.store.sources:
                return self.database_manager.store.sources[parsed]

            lowered = str(identifier).casefold()
            return next(
                (
                    source
                    for source in self.database_manager.store.sources.values()
                    if source.name.casefold() == lowered or str(source.id) == str(identifier)
                ),
                None,
            )

        if isinstance(identifier, uuid.UUID):
            return await self.get(identifier)

        try:
            parsed = uuid.UUID(str(identifier))
        except (TypeError, ValueError):
            parsed = None

        if parsed is not None:
            found = await self.get(parsed)
            if found is not None:
                return found

        lowered = str(identifier).casefold()
        async with self.database_manager.session() as session:
            return await session.scalar(select(Source).where(func.lower(Source.name) == lowered))

    async def get_by_name(self, project_id: uuid.UUID, name: str) -> Source | None:
        if self.database_manager.using_in_memory_store:
            lowered = name.casefold()
            return next(
                (
                    source
                    for source in self.database_manager.store.sources.values()
                    if source.project_id == project_id and source.name.casefold() == lowered
                ),
                None,
            )

        lowered = name.casefold()
        async with self.database_manager.session() as session:
            return await session.scalar(
                select(Source).where(
                    Source.project_id == project_id,
                    func.lower(Source.name) == lowered,
                )
            )

    async def add(self, source: Source) -> Source:
        if self.database_manager.using_in_memory_store:
            async with self.database_manager.store.lock:
                self.database_manager.store.sources[source.id] = source
            return source

        async with self.database_manager.session() as session:
            session.add(source)
            await session.commit()
            await session.refresh(source)
            return source

    async def update(self, source: Source) -> Source:
        if self.database_manager.using_in_memory_store:
            async with self.database_manager.store.lock:
                self.database_manager.store.sources[source.id] = source
            return source

        async with self.database_manager.session() as session:
            merged = await session.merge(source)
            await session.commit()
            await session.refresh(merged)
            return merged
