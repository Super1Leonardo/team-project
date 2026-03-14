from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.app.common.schemas import ParsedMessage


class BaseCollector(ABC):
    source_type: str

    @abstractmethod
    async def collect(
        self,
        source: dict[str, Any],
        *,
        limit: int = 100,
    ) -> list[ParsedMessage]:
        raise NotImplementedError
