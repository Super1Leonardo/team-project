from __future__ import annotations

import uuid

from pydantic import BaseModel


class CollectorTriggerResponse(BaseModel):
    source_id: uuid.UUID
    accepted: bool
    provider: str
    detail: str
