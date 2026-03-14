from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    DEFAULT_SPIKE_COOLDOWN_MINUTES,
    DEFAULT_SPIKE_THRESHOLD,
    DEFAULT_SPIKE_WINDOW_MINUTES,
)


class BrandCreate(BaseModel):
    project_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    keywords: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    risk_words: list[str] = Field(default_factory=list)
    spike_threshold: int = Field(default=DEFAULT_SPIKE_THRESHOLD, ge=1)
    spike_window_minutes: int = Field(default=DEFAULT_SPIKE_WINDOW_MINUTES, ge=1)
    spike_cooldown_minutes: int = Field(default=DEFAULT_SPIKE_COOLDOWN_MINUTES, ge=1)


class BrandUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    keywords: list[str] | None = None
    exceptions: list[str] | None = None
    risk_words: list[str] | None = None
    spike_threshold: int | None = Field(default=None, ge=1)
    spike_window_minutes: int | None = Field(default=None, ge=1)
    spike_cooldown_minutes: int | None = Field(default=None, ge=1)


class BrandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    keywords: list[str]
    exceptions: list[str]
    risk_words: list[str]
    spike_threshold: int
    spike_window_minutes: int
    spike_cooldown_minutes: int
    created_at: datetime
    updated_at: datetime
