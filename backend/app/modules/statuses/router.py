from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_statuses_service
from app.modules.statuses.schemas import ComponentStatusRead
from app.modules.statuses.service import StatusesService

router = APIRouter(prefix="/statuses", tags=["statuses"])


@router.get("", response_model=list[ComponentStatusRead])
async def list_statuses(service: StatusesService = Depends(get_statuses_service)) -> list[ComponentStatusRead]:
    return await service.list(refresh=True)
