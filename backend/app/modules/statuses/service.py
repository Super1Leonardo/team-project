from __future__ import annotations

from app.modules.health.service import HealthService
from app.modules.statuses.models import ComponentStatus
from app.modules.statuses.repository import ComponentStatusRepository


class StatusesService:
    def __init__(self, repository: ComponentStatusRepository, health_service: HealthService) -> None:
        self.repository = repository
        self.health_service = health_service

    async def list(self, *, refresh: bool = True) -> list[ComponentStatus]:
        if refresh:
            await self.health_service.get_health()
        return await self.repository.list()
