from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.common.enums import SourceType
from app.common.types import JSONValue


class SourceCreate(BaseModel):
    project_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    type: SourceType
    config: dict[str, JSONValue] = Field(default_factory=dict)
    is_active: bool = True


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    type: SourceType
    config: dict[str, JSONValue]
    is_active: bool
    last_collected_at: datetime | None
    last_error_at: datetime | None
    created_at: datetime
