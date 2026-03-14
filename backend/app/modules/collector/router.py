from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.api.dependencies import (
    get_collector_service,
    get_mention_ingest_service,
    get_mention_query_service,
)
from app.modules.collector.schemas import CollectorTriggerResponse
from app.modules.collector.service import CollectorService
from app.modules.mentions.schemas import MentionIngestRequest, MentionRead
from app.modules.mentions.services.ingest import MentionIngestService
from app.modules.mentions.services.query import MentionQueryService

router = APIRouter(tags=["collector"])


@router.post("/collector/trigger/{source_id}", response_model=CollectorTriggerResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_collection(
    source_id: uuid.UUID,
    service: CollectorService = Depends(get_collector_service),
) -> CollectorTriggerResponse:
    result = await service.trigger(source_id)
    return CollectorTriggerResponse(
        source_id=source_id,
        accepted=result.accepted,
        provider=result.provider,
        detail=result.detail,
    )


@router.post("/internal/mentions/ingest", response_model=MentionRead, status_code=status.HTTP_201_CREATED)
async def ingest_mention(
    payload: MentionIngestRequest,
    ingest_service: MentionIngestService = Depends(get_mention_ingest_service),
    query_service: MentionQueryService = Depends(get_mention_query_service),
) -> MentionRead:
    mention = await ingest_service.ingest(payload)
    return await query_service.get(mention.id)
