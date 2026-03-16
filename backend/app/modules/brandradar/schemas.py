from __future__ import annotations

from enum import Enum
from datetime import timedelta
from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field, model_validator


RelevanceLabel = Literal["relevant", "irrelevant"]
SentimentLabel = Literal["positive", "neutral", "negative"]
SourceType = Literal["telegram", "vk", "dzen", "rss", "website"]
T = TypeVar("T")


class MentionConfidenceThreshold(str, Enum):
    at_least_05 = "0.5"
    at_least_07 = "0.7"
    at_least_09 = "0.9"

    @property
    def threshold(self) -> float:
        return float(self.value)


class MentionPeriod(str, Enum):
    last_24_hours = "24h"
    last_7_days = "7d"
    last_30_days = "30d"

    @property
    def delta(self) -> timedelta:
        mapping = {
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        return mapping[self.value]


class MentionSentiment(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class ResponseMeta(BaseModel):
    total: int | None = None
    page: int | None = None
    page_size: int | None = None


class ApiEnvelope(BaseModel, Generic[T]):
    data: T
    meta: ResponseMeta | None = None


class ApiErrorBody(BaseModel):
    code: str
    message: str


class ApiErrorResponse(BaseModel):
    error: ApiErrorBody


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    keywords: list[str] = Field(min_length=1)
    exclude_keywords: list[str] = Field(default_factory=list)
    risk_words: list[str] = Field(default_factory=list)


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None
    risk_words: list[str] | None = None

    @model_validator(mode="after")
    def validate_non_empty_update(self) -> "ProjectUpdateRequest":
        if (
            self.name is None
            and self.keywords is None
            and self.exclude_keywords is None
            and self.risk_words is None
        ):
            raise ValueError("Provide at least one field to update the project.")
        if self.keywords is not None and len(self.keywords) == 0:
            raise ValueError("Project keywords must contain at least one item.")
        return self


class ProjectResponse(BaseModel):
    id: int
    name: str
    keywords: list[str]
    exclude_keywords: list[str]
    risk_words: list[str]
    created_at: datetime
    sources_count: int | None = None
    mentions_count: int | None = None


class SourceCreateRequest(BaseModel):
    source_type: SourceType
    source_config: dict[str, Any]
    is_active: bool = True
    poll_interval_s: int = Field(default=60, ge=1)


class SourceUpdateRequest(BaseModel):
    source_type: SourceType | None = None
    source_config: dict[str, Any] | None = None
    is_active: bool | None = None
    poll_interval_s: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_non_empty_update(self) -> "SourceUpdateRequest":
        if (
            self.source_type is None
            and self.source_config is None
            and self.is_active is None
            and self.poll_interval_s is None
        ):
            raise ValueError("Provide at least one field to update the source.")
        return self


class SourceResponse(BaseModel):
    id: int
    project_id: int
    source_type: SourceType
    source_config: dict[str, Any]
    is_active: bool
    poll_interval_s: int
    last_collected_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime
    raw_posts_count: int | None = None


class CollectorRunRequest(BaseModel):
    source_ids: list[int] = Field(default_factory=list)
    lookback_days: int = Field(default=30, ge=1, le=365)


class CollectorRunResponse(BaseModel):
    sources_checked: int
    sources_processed: int
    posts_saved: int
    errors: list[dict[str, Any]] = Field(default_factory=list)


class CollectorTriggerResponse(BaseModel):
    status: Literal["started"]
    sources_triggered: int


class CollectorSourceStatus(BaseModel):
    id: int
    project_id: int
    source_type: SourceType
    source_config: dict[str, Any]
    is_active: bool
    poll_interval_s: int
    last_collected_at: datetime | None = None
    last_error: str | None = None
    raw_posts_count: int
    status: Literal["ok", "error", "stale", "idle"]


class CollectorStatusResponse(BaseModel):
    ml_queue_size: int
    raw_posts_total: int
    raw_posts_processed: int
    raw_posts_pending: int
    raw_posts_failed: int
    processing_status: Literal["idle", "processing", "ready"]
    sources: list[CollectorSourceStatus]


class RawPostResponse(BaseModel):
    id: int
    source_id: int
    source_type: SourceType
    external_id: str
    url: str | None = None
    title: str | None = None
    text: str
    author: str | None = None
    published_at: datetime
    collected_at: datetime
    raw_meta: dict[str, Any]
    ml_processed: bool


class MentionResponse(BaseModel):
    id: int
    raw_post_id: int
    project_id: int
    source_id: int
    source_type: SourceType
    external_id: str
    url: str | None = None
    title: str | None = None
    text: str
    author: str | None = None
    published_at: datetime
    collected_at: datetime
    relevance_score: float
    relevance_label: RelevanceLabel
    sentiment_score: float
    sentiment_label: SentimentLabel
    has_risk_words: bool
    dedup_group_id: int | None = None
    is_primary: bool
    processed_at: datetime


class MentionClusterResponse(BaseModel):
    cluster_id: int
    dedup_group_id: int | None = None
    mentions_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    representative_mention_id: int
    raw_post_id: int
    project_id: int
    source_id: int
    source_type: SourceType
    external_id: str
    url: str | None = None
    title: str | None = None
    text: str
    author: str | None = None
    published_at: datetime
    collected_at: datetime
    relevance_score: float
    relevance_label: RelevanceLabel
    sentiment_score: float
    sentiment_label: SentimentLabel
    has_risk_words: bool
    processed_at: datetime


class MLQueueItem(BaseModel):
    raw_post_id: int
    source_id: int
    project_id: int
    source_type: SourceType
    external_id: str
    url: str | None = None
    title: str | None = None
    text: str
    author: str | None = None
    published_at: datetime
    collected_at: datetime
    raw_meta: dict[str, Any]
    keywords: list[str]
    exclude_keywords: list[str]
    risk_words: list[str]


class MLQueueResponse(BaseModel):
    count: int
    items: list[MLQueueItem]


class MLResultWriteItem(BaseModel):
    raw_post_id: int
    relevance_score: float
    relevance_label: RelevanceLabel
    sentiment_score: float
    sentiment_label: SentimentLabel
    has_risk_words: bool = False
    embedding: list[float] | None = Field(default=None, min_length=384, max_length=384)
    dedup_group_id: int | None = None
    is_primary: bool = True
    processed_at: datetime | None = None


class MLResultsPushRequest(BaseModel):
    results: list[MLResultWriteItem] = Field(min_length=1)


class MLResultsPushResponse(BaseModel):
    stored_count: int
    synced_count: int
    projects: dict[str, dict[str, int]]
    message: str


class MLRunResponse(BaseModel):
    batch_size: int
    stored_count: int
    synced_count: int
    projects: dict[str, dict[str, int]]


class MLRemotePredictResponse(BaseModel):
    queued_count: int
    remote_url: str
    remote_results_count: int
    stored_count: int | None = None
    synced_count: int | None = None
    projects: dict[str, dict[str, int]] = Field(default_factory=dict)
    persisted: bool
    remote_response: Any


class BrandRadarHealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    postgres: Literal["healthy", "unhealthy"]
    clickhouse: Literal["healthy", "unhealthy"]
    ml: Literal["healthy", "unhealthy"]
    ml_url: str
    ml_error: str | None = None
    ml_queue_size: int
