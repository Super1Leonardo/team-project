from __future__ import annotations

import uuid

from app.infra.db.session import InMemoryStore
from app.modules.projects.models import Project


class ProjectRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    async def list(self) -> list[Project]:
        return sorted(self.store.projects.values(), key=lambda item: item.created_at, reverse=True)

    async def get(self, project_id: uuid.UUID) -> Project | None:
        return self.store.projects.get(project_id)

    async def get_by_name(self, name: str) -> Project | None:
        lowered = name.casefold()
        return next((project for project in self.store.projects.values() if project.name.casefold() == lowered), None)

    async def add(self, project: Project) -> Project:
        async with self.store.lock:
            self.store.projects[project.id] = project
        return project
