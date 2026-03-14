from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.common.enums import CriticalityLabel, RelevanceLabel, SentimentLabel


@dataclass(slots=True)
class MLRequest:
    project_id: uuid.UUID
    source_id: uuid.UUID
    title: str
    text: str
    normalized_text: str
    rule_relevance_label: RelevanceLabel
    risk_words_hit: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MLPrediction:
    relevance_label: RelevanceLabel
    relevance_score: float
    sentiment_label: SentimentLabel
    sentiment_score: float
    criticality_label: CriticalityLabel
    criticality_score: float
    risk_words_hit: list[str]
    cluster_id: str | None = None
    provider: str | None = None
    version: str | None = None


@dataclass(slots=True)
class MLResultEnvelope:
    prediction: MLPrediction
    used_fallback: bool = False
    failure_reason: str | None = None


class MLPort(Protocol):
    async def predict(self, request: MLRequest) -> MLResultEnvelope: ...

    async def healthcheck(self) -> tuple[bool, str | None, dict[str, object] | None]: ...
