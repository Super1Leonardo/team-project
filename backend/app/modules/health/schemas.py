from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.common.enums import ComponentHealthStatus
from app.common.types import JSONValue


class HealthComponentRead(BaseModel):
    component_name: str
    component_type: str
    status: ComponentHealthStatus
    latency_ms: int | None = None
    last_error: str | None = None
    meta: dict[str, JSONValue] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: ComponentHealthStatus
    checked_at: datetime
    components: list[HealthComponentRead]
