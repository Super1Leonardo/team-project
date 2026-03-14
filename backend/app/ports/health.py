from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.common.enums import ComponentHealthStatus


@dataclass(slots=True)
class HealthCheckResult:
    component_name: str
    component_type: str
    status: ComponentHealthStatus
    latency_ms: int | None = None
    last_error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)
