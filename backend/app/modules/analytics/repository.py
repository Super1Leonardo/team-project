from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from sqlalchemy import select

from app.core.time import ensure_utc
from app.infra.db.session import DatabaseManager
from app.modules.analytics.schemas import MentionsChartBucket, MentionsChartFilters, MentionsChartResponse
from app.modules.mentions.models import Mention
from app.modules.sources.models import Source


class AnalyticsRepository:
    def __init__(self, database_manager: DatabaseManager) -> None:
        self.database_manager = database_manager

    async def mentions_chart(self, filters: MentionsChartFilters) -> MentionsChartResponse:
        mentions, source_map = await self._load_mentions(filters)
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
            source = source_map.get(mention.source_id)
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

    async def _load_mentions(self, filters: MentionsChartFilters) -> tuple[list[Mention], dict]:
        if self.database_manager.using_in_memory_store:
            mentions = list(self.database_manager.store.mentions.values())

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
                    if (source := self.database_manager.store.sources.get(mention.source_id)) is not None
                    and source.type == filters.source_type
                ]
            return mentions, dict(self.database_manager.store.sources)

        statement = select(Mention, Source).join(Source, Mention.source_id == Source.id)
        if filters.date_from is not None:
            statement = statement.where(Mention.created_at >= ensure_utc(filters.date_from))
        if filters.date_to is not None:
            statement = statement.where(Mention.created_at <= ensure_utc(filters.date_to))
        if filters.brand_id is not None:
            statement = statement.where(Mention.brand_id == filters.brand_id)
        if filters.sentiment is not None:
            statement = statement.where(Mention.sentiment_label == filters.sentiment)
        if filters.relevance is not None:
            statement = statement.where(Mention.relevance_label == filters.relevance)
        if filters.criticality is not None:
            statement = statement.where(Mention.criticality_label == filters.criticality)
        if filters.source_type is not None:
            statement = statement.where(Source.type == filters.source_type)

        async with self.database_manager.session() as session:
            rows = (await session.execute(statement)).all()

        mentions = [row[0] for row in rows]
        source_map = {row[1].id: row[1] for row in rows}
        return mentions, source_map
