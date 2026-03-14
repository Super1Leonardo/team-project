from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.common.enums import EventLevel
from app.common.types import JSONValue


class EventLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    level: EventLevel
    entity_type: str
    entity_id: uuid.UUID | None = None
    payload: dict[str, JSONValue]
    created_at: datetime
