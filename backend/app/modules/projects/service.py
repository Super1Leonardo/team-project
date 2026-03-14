from __future__ import annotations

import uuid

from app.core.constants import EVENT_PROJECT_CREATED
from app.core.exceptions import ConflictError
from app.core.time import utc_now
from app.modules.events.service import EventLogService
from app.modules.projects.models import Project
from app.modules.projects.repository import ProjectRepository
from app.modules.projects.schemas import ProjectCreate


class ProjectService:
    def __init__(self, repository: ProjectRepository, event_log_service: EventLogService) -> None:
        self.repository = repository
        self.event_log_service = event_log_service

    async def list(self) -> list[Project]:
        return await self.repository.list()

    async def create(self, data: ProjectCreate) -> Project:
        name = data.name.strip()
        existing = await self.repository.get_by_name(name)
        if existing is not None:
            raise ConflictError(f"Project with name '{name}' already exists")

        now = utc_now()
        project = Project(
            id=uuid.uuid4(),
            name=name,
            description=(data.description or "").strip() or None,
            created_at=now,
            updated_at=now,
        )
        saved = await self.repository.add(project)
        await self.event_log_service.record(
            EVENT_PROJECT_CREATED,
            "project",
            entity_id=saved.id,
            payload={"name": saved.name},
        )
        return saved
