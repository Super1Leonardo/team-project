from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_event_log_service
from app.common.enums import EventLevel
from app.common.pagination import Page
from app.modules.events.schemas import EventLogRead
from app.modules.events.service import EventLogService

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=Page[EventLogRead])
async def list_events(
    event_type: str | None = Query(default=None),
    level: EventLevel | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: EventLogService = Depends(get_event_log_service),
) -> Page[EventLogRead]:
    items, total = await service.list(event_type=event_type, level=level, limit=limit, offset=offset)
    return Page(items=items, total=total, limit=limit, offset=offset)
