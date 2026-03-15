from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ParserSource = Literal["telegram", "website", "rss"]


class ReactionInfo(BaseModel):
    key: str
    count: int
    type: str


class MessageSource(BaseModel):
    channel_id: int
    title: str
    username: str | None = None
    requested_as: str


class ParsedMessage(BaseModel):
    message_uid: str | None = None
    project_id: str | None = None
    source_type: ParserSource = "telegram"
    id: int
    title: str | None = None
    text: str
    date: datetime
    views: int | None = None
    forwards: int | None = None
    post_author: str | None = None
    url: str | None = None
    like_count: int | None = None
    dislike_count: int | None = None
    reactions: list[ReactionInfo] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
    source: MessageSource


class ChannelParseResult(BaseModel):
    requested_as: str
    title: str | None = None
    username: str | None = None
    status: str
    error: str | None = None
    messages: list[ParsedMessage] = Field(default_factory=list)


class ParseResponse(BaseModel):
    authorized: bool
    count: int
    channels: list[str]
    items: list[ParsedMessage]
    results: list[ChannelParseResult]
    stored_count: int | None = None
    storage_backend: str | None = None


class StoredMessagesResponse(BaseModel):
    count: int
    storage_backend: str
    items: list[ParsedMessage]


class MLResultInput(BaseModel):
    message_uid: str = Field(min_length=1)
    project_id: str = "default"
    relevance_label: bool | None = None
    relevance_score: float | None = None
    sentiment_label: str | None = None
    sentiment_score: float | None = None
    aggression_score: float | None = None
    womp_score: float | None = None
    dedup_group_id: str | None = None
    is_canonical: bool = True
    story_cluster_id: str | None = None
    model_version: str | None = None
    features: dict[str, Any] | None = None
    processed_at: datetime | None = None


class MLOffsetUpdate(BaseModel):
    consumer_name: str = Field(min_length=1)
    last_collected_at: datetime | None = None
    last_message_uid: str | None = None

    @model_validator(mode="after")
    def validate_progress_marker(self) -> "MLOffsetUpdate":
        if self.last_collected_at is None and self.last_message_uid is None:
            raise ValueError(
                "Provide last_collected_at or last_message_uid when updating ML offset."
            )
        return self


class MLResultsWriteRequest(BaseModel):
    results: list[MLResultInput] = Field(min_length=1)
    offset: MLOffsetUpdate | None = None


class MLResultsWriteResponse(BaseModel):
    stored_count: int
    offset_updated: bool
    consumer_name: str | None = None
    message: str
