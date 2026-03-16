from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from backend.app.common.schemas import ParsedMessage


class BaseCollector(ABC):
    source_type: str

    @abstractmethod
    async def collect(
        self,
        source: dict[str, Any],
        *,
        published_after: datetime | None = None,
    ) -> list[ParsedMessage]:
        raise NotImplementedError
