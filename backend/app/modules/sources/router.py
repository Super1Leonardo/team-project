from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_source_service
from app.modules.sources.schemas import SourceCreate, SourceRead
from app.modules.sources.service import SourceService

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceRead])
async def list_sources(
    project_id: uuid.UUID | None = Query(default=None),
    service: SourceService = Depends(get_source_service),
) -> list[SourceRead]:
    return await service.list(project_id=project_id)


@router.post("", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
async def create_source(
    payload: SourceCreate,
    service: SourceService = Depends(get_source_service),
) -> SourceRead:
    return await service.create(payload)
