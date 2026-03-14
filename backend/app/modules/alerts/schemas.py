from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.common.enums import AlertStatus, AlertType
from app.common.types import JSONValue


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    brand_id: uuid.UUID
    brand_name: str | None = None
    type: AlertType
    status: AlertStatus
    threshold: int
    window_minutes: int
    cooldown_minutes: int
    mentions_count: int
    payload: dict[str, JSONValue]
    created_at: datetime
