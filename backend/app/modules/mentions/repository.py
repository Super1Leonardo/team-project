from __future__ import annotations

import uuid

from app.common.enums import DuplicateMode
from app.common.types import normalize_text
from app.core.time import ensure_utc
from app.infra.db.session import InMemoryStore
from app.modules.mentions.models import Mention
from app.modules.mentions.schemas import MentionFilters


class MentionRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    async def add(self, mention: Mention) -> Mention:
        async with self.store.lock:
            self.store.mentions[mention.id] = mention
        return mention

    async def get(self, mention_id: uuid.UUID) -> Mention | None:
        return self.store.mentions.get(mention_id)

    async def find_by_url_hash(self, project_id: uuid.UUID, source_id: uuid.UUID, url_hash: str | None) -> Mention | None:
        if not url_hash:
            return None
        return next(
            (
                mention
                for mention in self.store.mentions.values()
                if mention.project_id == project_id and mention.source_id == source_id and mention.url_hash == url_hash
            ),
            None,
        )

    async def find_by_content_hash(self, project_id: uuid.UUID, source_id: uuid.UUID, content_hash: str) -> Mention | None:
        return next(
            (
                mention
                for mention in self.store.mentions.values()
                if mention.project_id == project_id
                and mention.source_id == source_id
                and mention.content_hash == content_hash
            ),
            None,
        )

    async def list(self, filters: MentionFilters) -> tuple[list[Mention], int]:
        items = self._apply_filters(filters)
        total = len(items)
        paged = items[filters.offset : filters.offset + filters.limit]
        return paged, total

    async def scan(self, filters: MentionFilters | None = None) -> list[Mention]:
        return self._apply_filters(filters or MentionFilters())

    def _apply_filters(self, filters: MentionFilters) -> list[Mention]:
        items = list(self.store.mentions.values())

        if filters.project_id is not None:
            items = [mention for mention in items if mention.project_id == filters.project_id]
        if filters.date_from is not None:
            items = [mention for mention in items if ensure_utc(mention.created_at) >= ensure_utc(filters.date_from)]
        if filters.date_to is not None:
            items = [mention for mention in items if ensure_utc(mention.created_at) <= ensure_utc(filters.date_to)]
        if filters.source_id is not None:
            items = [mention for mention in items if mention.source_id == filters.source_id]
        if filters.source_type is not None:
            items = [
                mention
                for mention in items
                if (source := self.store.sources.get(mention.source_id)) is not None and source.type == filters.source_type
            ]
        if filters.brand_id is not None:
            items = [mention for mention in items if mention.brand_id == filters.brand_id]
        if filters.relevance is not None:
            items = [mention for mention in items if mention.relevance_label == filters.relevance]
        if filters.sentiment is not None:
            items = [mention for mention in items if mention.sentiment_label == filters.sentiment]
        if filters.criticality is not None:
            items = [mention for mention in items if mention.criticality_label == filters.criticality]
        if filters.min_relevance_score is not None:
            items = [mention for mention in items if mention.relevance_score >= filters.min_relevance_score]
        if filters.min_sentiment_score is not None:
            items = [mention for mention in items if mention.sentiment_score >= filters.min_sentiment_score]
        if filters.duplicates == DuplicateMode.EXCLUDE:
            items = [mention for mention in items if not mention.is_duplicate]
        elif filters.duplicates == DuplicateMode.ONLY:
            items = [mention for mention in items if mention.is_duplicate]
        if filters.q:
            query = normalize_text(filters.q)
            items = [
                mention
                for mention in items
                if query in normalize_text(f"{mention.title} {mention.text}")
            ]

        return sorted(items, key=lambda item: (ensure_utc(item.created_at), ensure_utc(item.ingested_at)), reverse=True)
