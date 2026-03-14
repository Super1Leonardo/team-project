from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_health_service
from app.modules.health.schemas import HealthResponse
from app.modules.health.service import HealthService

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def get_health(service: HealthService = Depends(get_health_service)) -> HealthResponse:
    return await service.get_health()
