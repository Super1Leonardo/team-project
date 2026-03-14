from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.common.enums import ComponentHealthStatus
from app.common.types import JSONValue


class ComponentStatusRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    component_name: str
    component_type: str
    status: ComponentHealthStatus
    latency_ms: int | None = None
    last_seen_at: datetime
    last_error: str | None = None
    meta: dict[str, JSONValue]
