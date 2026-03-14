from __future__ import annotations

from enum import StrEnum


class SentimentLabel(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class RelevanceLabel(StrEnum):
    RELEVANT = "relevant"
    IRRELEVANT = "irrelevant"
    REVIEW = "review"

    @property
    def mark(self) -> str:
        return {
            RelevanceLabel.RELEVANT: "+",
            RelevanceLabel.IRRELEVANT: "-",
            RelevanceLabel.REVIEW: "~",
        }[self]


class CriticalityLabel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SourceType(StrEnum):
    RSS = "rss"
    TELEGRAM = "telegram"
    VK = "vk"
    WEB = "web"
    NEWS_SITE = "news_site"
    OTHER = "other"


class ComponentHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


class AlertType(StrEnum):
    SPIKE_NEGATIVE = "spike_negative"


class AlertStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    CLOSED = "closed"


class EventLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class DuplicateMode(StrEnum):
    INCLUDE = "include"
    EXCLUDE = "exclude"
    ONLY = "only"


def relevance_mark(label: RelevanceLabel | str) -> str:
    return RelevanceLabel(label).mark
