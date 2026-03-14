from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_analytics_service
from app.common.enums import CriticalityLabel, RelevanceLabel, SentimentLabel, SourceType
from app.modules.analytics.schemas import MentionsChartFilters, MentionsChartResponse
from app.modules.analytics.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/mentions-chart", response_model=MentionsChartResponse)
async def get_mentions_chart(
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    brand_id: uuid.UUID | None = Query(default=None),
    source_type: SourceType | None = Query(default=None),
    sentiment: SentimentLabel | None = Query(default=None),
    relevance: RelevanceLabel | None = Query(default=None),
    criticality: CriticalityLabel | None = Query(default=None),
    service: AnalyticsService = Depends(get_analytics_service),
) -> MentionsChartResponse:
    filters = MentionsChartFilters(
        date_from=date_from,
        date_to=date_to,
        brand_id=brand_id,
        source_type=source_type,
        sentiment=sentiment,
        relevance=relevance,
        criticality=criticality,
    )
    return await service.mentions_chart(filters)
