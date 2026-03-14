from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from app.core.time import ensure_utc
from app.infra.db.session import InMemoryStore
from app.modules.analytics.schemas import MentionsChartBucket, MentionsChartFilters, MentionsChartResponse


class AnalyticsRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    async def mentions_chart(self, filters: MentionsChartFilters) -> MentionsChartResponse:
        mentions = list(self.store.mentions.values())

        if filters.date_from is not None:
            mentions = [mention for mention in mentions if ensure_utc(mention.created_at) >= ensure_utc(filters.date_from)]
        if filters.date_to is not None:
            mentions = [mention for mention in mentions if ensure_utc(mention.created_at) <= ensure_utc(filters.date_to)]
        if filters.brand_id is not None:
            mentions = [mention for mention in mentions if mention.brand_id == filters.brand_id]
        if filters.sentiment is not None:
            mentions = [mention for mention in mentions if mention.sentiment_label == filters.sentiment]
        if filters.relevance is not None:
            mentions = [mention for mention in mentions if mention.relevance_label == filters.relevance]
        if filters.criticality is not None:
            mentions = [mention for mention in mentions if mention.criticality_label == filters.criticality]
        if filters.source_type is not None:
            mentions = [
                mention
                for mention in mentions
                if (source := self.store.sources.get(mention.source_id)) is not None and source.type == filters.source_type
            ]

        mentions = sorted(mentions, key=lambda item: ensure_utc(item.created_at))

        if filters.date_from and filters.date_to:
            period_hours = max((ensure_utc(filters.date_to) - ensure_utc(filters.date_from)).total_seconds() / 3600, 1)
        else:
            period_hours = 24 * 30
        granularity = "hour" if period_hours <= 72 else "day"

        buckets_map: dict[datetime, dict[str, object]] = {}
        totals = defaultdict(int)

        for mention in mentions:
            bucket_start = self._bucket_start(ensure_utc(mention.created_at), granularity)
            source = self.store.sources.get(mention.source_id)
            bucket = buckets_map.setdefault(
                bucket_start,
                {"total": 0, "by_sentiment": defaultdict(int), "by_source_type": defaultdict(int)},
            )
            bucket["total"] += 1
            bucket["by_sentiment"][mention.sentiment_label.value] += 1
            if source is not None:
                bucket["by_source_type"][source.type.value] += 1

            totals["total"] += 1
            totals[mention.sentiment_label.value] += 1

        buckets = [
            MentionsChartBucket(
                bucket_start=bucket_start,
                total=int(payload["total"]),
                by_sentiment=dict(payload["by_sentiment"]),
                by_source_type=dict(payload["by_source_type"]),
            )
            for bucket_start, payload in sorted(buckets_map.items(), key=lambda item: item[0])
        ]

        return MentionsChartResponse(granularity=granularity, buckets=buckets, totals=dict(totals))

    @staticmethod
    def _bucket_start(value: datetime, granularity: str) -> datetime:
        if granularity == "hour":
            return value.replace(minute=0, second=0, microsecond=0)
        return value.replace(hour=0, minute=0, second=0, microsecond=0)
