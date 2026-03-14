from __future__ import annotations

import uuid

from app.common.enums import ComponentHealthStatus, EventLevel
from app.core.constants import EVENT_HEALTH_CHECK_FAILED
from app.core.time import utc_now
from app.infra.health.registry import HealthRegistry
from app.modules.events.service import EventLogService
from app.modules.health.schemas import HealthComponentRead, HealthResponse
from app.modules.statuses.models import ComponentStatus
from app.modules.statuses.repository import ComponentStatusRepository


class HealthService:
    def __init__(
        self,
        registry: HealthRegistry,
        status_repository: ComponentStatusRepository,
        event_log_service: EventLogService,
    ) -> None:
        self.registry = registry
        self.status_repository = status_repository
        self.event_log_service = event_log_service

    async def get_health(self) -> HealthResponse:
        checked_at = utc_now()
        checks = await self.registry.run_checks()
        components: list[HealthComponentRead] = []

        for check in checks:
            status_record = ComponentStatus(
                id=uuid.uuid4(),
                component_name=check.component_name,
                component_type=check.component_type,
                status=check.status,
                latency_ms=check.latency_ms,
                last_seen_at=checked_at,
                last_error=check.last_error,
                meta=dict(check.meta),
            )
            await self.status_repository.upsert(status_record)
            components.append(
                HealthComponentRead(
                    component_name=check.component_name,
                    component_type=check.component_type,
                    status=check.status,
                    latency_ms=check.latency_ms,
                    last_error=check.last_error,
                    meta=dict(check.meta),
                )
            )
            if check.status != ComponentHealthStatus.HEALTHY:
                await self.event_log_service.record(
                    EVENT_HEALTH_CHECK_FAILED,
                    "component",
                    level=EventLevel.ERROR if check.status == ComponentHealthStatus.DOWN else EventLevel.WARNING,
                    payload={
                        "component_name": check.component_name,
                        "status": check.status.value,
                        "last_error": check.last_error,
                    },
                )

        overall_status = ComponentHealthStatus.HEALTHY
        if any(component.status == ComponentHealthStatus.DOWN for component in components):
            overall_status = ComponentHealthStatus.DOWN
        elif any(component.status == ComponentHealthStatus.DEGRADED for component in components):
            overall_status = ComponentHealthStatus.DEGRADED

        return HealthResponse(status=overall_status, checked_at=checked_at, components=components)
