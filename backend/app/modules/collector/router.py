from fastapi import APIRouter, Depends, Query

from backend.app.api.dependencies import get_collector_service
from backend.app.modules.collector.schemas import ParseResponse
from backend.app.modules.collector.service import CollectorService

router = APIRouter(tags=["collector"])


@router.get("/messages", response_model=ParseResponse)
async def parse_messages(
    limit_per_channel: int = Query(default=20, ge=1, le=100),
    channel: list[str] | None = Query(default=None),
    store: bool = Query(default=True),
    service: CollectorService = Depends(get_collector_service),
):
    return await service.collect_messages(
        limit_per_channel=limit_per_channel,
        channel=channel,
        store=store,
    )
