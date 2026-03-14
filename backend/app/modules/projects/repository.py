from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.infra.db.session import DatabaseManager
from app.modules.projects.models import Project


class ProjectRepository:
    def __init__(self, database_manager: DatabaseManager) -> None:
        self.database_manager = database_manager

    async def list(self) -> list[Project]:
        if self.database_manager.using_in_memory_store:
            return sorted(self.database_manager.store.projects.values(), key=lambda item: item.created_at, reverse=True)

        async with self.database_manager.session() as session:
            result = await session.scalars(select(Project).order_by(Project.created_at.desc()))
            return list(result.all())

    async def get(self, project_id: uuid.UUID) -> Project | None:
        if self.database_manager.using_in_memory_store:
            return self.database_manager.store.projects.get(project_id)

        async with self.database_manager.session() as session:
            return await session.get(Project, project_id)

    async def get_by_name(self, name: str) -> Project | None:
        if self.database_manager.using_in_memory_store:
            lowered = name.casefold()
            return next(
                (
                    project
                    for project in self.database_manager.store.projects.values()
                    if project.name.casefold() == lowered
                ),
                None,
            )

        lowered = name.casefold()
        async with self.database_manager.session() as session:
            result = await session.scalar(select(Project).where(func.lower(Project.name) == lowered))
            return result

    async def add(self, project: Project) -> Project:
        if self.database_manager.using_in_memory_store:
            async with self.database_manager.store.lock:
                self.database_manager.store.projects[project.id] = project
            return project

        async with self.database_manager.session() as session:
            session.add(project)
            await session.commit()
            await session.refresh(project)
            return project
