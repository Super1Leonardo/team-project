from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_alert_service
from app.common.enums import AlertStatus
from app.modules.alerts.schemas import AlertRead
from app.modules.alerts.service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertRead])
async def list_alerts(
    project_id: uuid.UUID | None = Query(default=None),
    brand_id: uuid.UUID | None = Query(default=None),
    status: AlertStatus | None = Query(default=None),
    service: AlertService = Depends(get_alert_service),
) -> list[AlertRead]:
    return await service.list(project_id=project_id, brand_id=brand_id, status=status)
