from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class CollectorTriggerResult:
    accepted: bool
    provider: str
    detail: str


class CollectorPort(Protocol):
    async def trigger(self, source_id: uuid.UUID) -> CollectorTriggerResult: ...

    async def healthcheck(self) -> tuple[bool, str | None, dict[str, object] | None]: ...
