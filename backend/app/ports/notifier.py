from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(slots=True)
class NotificationPayload:
    alert_id: uuid.UUID
    project_id: uuid.UUID
    brand_id: uuid.UUID
    brand_name: str
    alert_type: str
    mentions_count: int
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NotificationResult:
    delivered: bool
    provider: str
    detail: str | None = None


class NotifierPort(Protocol):
    async def send(self, payload: NotificationPayload) -> NotificationResult: ...

    async def healthcheck(self) -> tuple[bool, str | None, dict[str, object] | None]: ...
