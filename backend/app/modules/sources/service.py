from __future__ import annotations

import uuid

from app.core.constants import EVENT_SOURCE_CREATED
from app.core.exceptions import ConflictError, NotFoundError
from app.core.time import utc_now
from app.modules.events.service import EventLogService
from app.modules.projects.repository import ProjectRepository
from app.modules.sources.models import Source
from app.modules.sources.repository import SourceRepository
from app.modules.sources.schemas import SourceCreate


class SourceService:
    def __init__(
        self,
        repository: SourceRepository,
        project_repository: ProjectRepository,
        event_log_service: EventLogService,
    ) -> None:
        self.repository = repository
        self.project_repository = project_repository
        self.event_log_service = event_log_service

    async def list(self, project_id: uuid.UUID | None = None) -> list[Source]:
        return await self.repository.list(project_id=project_id)

    async def create(self, data: SourceCreate) -> Source:
        project = await self.project_repository.get(data.project_id)
        if project is None:
            raise NotFoundError(f"Project '{data.project_id}' not found")

        name = data.name.strip()
        existing = await self.repository.get_by_name(data.project_id, name)
        if existing is not None:
            raise ConflictError(f"Source with name '{name}' already exists in this project")

        source = Source(
            id=uuid.uuid4(),
            project_id=data.project_id,
            name=name,
            type=data.type,
            config=dict(data.config),
            is_active=data.is_active,
            last_collected_at=None,
            last_error_at=None,
            created_at=utc_now(),
        )
        saved = await self.repository.add(source)
        await self.event_log_service.record(
            EVENT_SOURCE_CREATED,
            "source",
            entity_id=saved.id,
            payload={"project_id": str(saved.project_id), "type": saved.type.value, "name": saved.name},
        )
        return saved
