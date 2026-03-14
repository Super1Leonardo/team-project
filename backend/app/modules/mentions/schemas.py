from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.common.enums import CriticalityLabel, DuplicateMode, RelevanceLabel, SentimentLabel, SourceType


class MentionIngestMetadata(BaseModel):
    author: str | None = None
    channel: str | None = None
    site: str | None = None


class MentionIngestRequest(BaseModel):
    source_id: uuid.UUID | str
    external_id: str | None = None
    title: str = ""
    text: str = ""
    raw_url: str | None = None
    created_at: datetime | str
    metadata: MentionIngestMetadata = Field(default_factory=MentionIngestMetadata)

    @model_validator(mode="after")
    def validate_content(self) -> "MentionIngestRequest":
        if not (self.title or "").strip() and not (self.text or "").strip():
            raise ValueError("title or text must be provided")
        return self


class MentionFilters(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    source_id: uuid.UUID | None = None
    source_type: SourceType | None = None
    brand_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    relevance: RelevanceLabel | None = None
    sentiment: SentimentLabel | None = None
    criticality: CriticalityLabel | None = None
    min_relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    min_sentiment_score: float | None = Field(default=None, ge=0.0, le=1.0)
    duplicates: DuplicateMode = DuplicateMode.INCLUDE
    q: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class MentionSourceDTO(BaseModel):
    id: uuid.UUID
    name: str
    type: SourceType


class MentionBrandDTO(BaseModel):
    id: uuid.UUID
    name: str


class MentionMLData(BaseModel):
    relevance: RelevanceLabel
    relevance_mark: str
    relevance_score: float
    sentiment: SentimentLabel
    sentiment_score: float
    criticality: CriticalityLabel
    criticality_score: float
    risk_words_hit: list[str]
    cluster_id: str | None = None
    provider: str | None = None
    version: str | None = None


class MentionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    brand: MentionBrandDTO | None = None
    source: MentionSourceDTO
    external_id: str | None = None
    title: str
    text: str
    raw_url: str | None = None
    created_at: datetime
    ingested_at: datetime
    is_duplicate: bool
    is_duplicate_of: uuid.UUID | None = None
    ml_data: MentionMLData
