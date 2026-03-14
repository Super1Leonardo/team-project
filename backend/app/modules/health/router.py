from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_health_service
from backend.app.modules.health.service import HealthService

router = APIRouter(tags=["health"])


@router.get("/health")
async def healthcheck(service: HealthService = Depends(get_health_service)):
    return service.healthcheck()
