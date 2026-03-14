from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.common.enums import CriticalityLabel, RelevanceLabel, SentimentLabel, SourceType


class MentionsChartFilters(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    brand_id: uuid.UUID | None = None
    source_type: SourceType | None = None
    sentiment: SentimentLabel | None = None
    relevance: RelevanceLabel | None = None
    criticality: CriticalityLabel | None = None


class MentionsChartBucket(BaseModel):
    bucket_start: datetime
    total: int
    by_sentiment: dict[str, int] = Field(default_factory=dict)
    by_source_type: dict[str, int] = Field(default_factory=dict)


class MentionsChartResponse(BaseModel):
    granularity: str
    buckets: list[MentionsChartBucket]
    totals: dict[str, int]
