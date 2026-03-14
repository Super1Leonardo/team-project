from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_mention_query_service
from app.common.enums import CriticalityLabel, DuplicateMode, RelevanceLabel, SentimentLabel, SourceType
from app.common.pagination import Page
from app.modules.mentions.schemas import MentionFilters, MentionRead
from app.modules.mentions.services.query import MentionQueryService

router = APIRouter(prefix="/mentions", tags=["mentions"])


@router.get("", response_model=Page[MentionRead])
async def list_mentions(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    source_id: uuid.UUID | None = Query(default=None),
    source_type: SourceType | None = Query(default=None),
    brand_id: uuid.UUID | None = Query(default=None),
    relevance: RelevanceLabel | None = Query(default=None),
    sentiment: SentimentLabel | None = Query(default=None),
    criticality: CriticalityLabel | None = Query(default=None),
    min_relevance_score: float | None = Query(default=None),
    min_sentiment_score: float | None = Query(default=None),
    duplicates: DuplicateMode = Query(default=DuplicateMode.INCLUDE),
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: MentionQueryService = Depends(get_mention_query_service),
) -> Page[MentionRead]:
    filters = MentionFilters(
        date_from=date_from,
        date_to=date_to,
        source_id=source_id,
        source_type=source_type,
        brand_id=brand_id,
        relevance=relevance,
        sentiment=sentiment,
        criticality=criticality,
        min_relevance_score=min_relevance_score,
        min_sentiment_score=min_sentiment_score,
        duplicates=duplicates,
        q=q,
        limit=limit,
        offset=offset,
    )
    return await service.list(filters)


@router.get("/{mention_id}", response_model=MentionRead)
async def get_mention(
    mention_id: uuid.UUID,
    service: MentionQueryService = Depends(get_mention_query_service),
) -> MentionRead:
    return await service.get(mention_id)
