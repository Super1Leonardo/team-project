from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select

from app.common.enums import DuplicateMode
from app.common.types import normalize_text
from app.core.time import ensure_utc
from app.infra.db.session import DatabaseManager
from app.modules.mentions.models import Mention
from app.modules.mentions.schemas import MentionFilters
from app.modules.sources.models import Source


class MentionRepository:
    def __init__(self, database_manager: DatabaseManager) -> None:
        self.database_manager = database_manager

    async def add(self, mention: Mention) -> Mention:
        if self.database_manager.using_in_memory_store:
            async with self.database_manager.store.lock:
                self.database_manager.store.mentions[mention.id] = mention
            return mention

        async with self.database_manager.session() as session:
            session.add(mention)
            await session.commit()
            await session.refresh(mention)
            return mention

    async def get(self, mention_id: uuid.UUID) -> Mention | None:
        if self.database_manager.using_in_memory_store:
            return self.database_manager.store.mentions.get(mention_id)

        async with self.database_manager.session() as session:
            return await session.get(Mention, mention_id)

    async def find_by_url_hash(self, project_id: uuid.UUID, source_id: uuid.UUID, url_hash: str | None) -> Mention | None:
        if not url_hash:
            return None

        if self.database_manager.using_in_memory_store:
            return next(
                (
                    mention
                    for mention in self.database_manager.store.mentions.values()
                    if mention.project_id == project_id and mention.source_id == source_id and mention.url_hash == url_hash
                ),
                None,
            )

        async with self.database_manager.session() as session:
            return await session.scalar(
                select(Mention)
                .where(
                    Mention.project_id == project_id,
                    Mention.source_id == source_id,
                    Mention.url_hash == url_hash,
                )
                .order_by(Mention.ingested_at.asc())
                .limit(1)
            )

    async def find_by_content_hash(self, project_id: uuid.UUID, source_id: uuid.UUID, content_hash: str) -> Mention | None:
        if self.database_manager.using_in_memory_store:
            return next(
                (
                    mention
                    for mention in self.database_manager.store.mentions.values()
                    if mention.project_id == project_id
                    and mention.source_id == source_id
                    and mention.content_hash == content_hash
                ),
                None,
            )

        async with self.database_manager.session() as session:
            return await session.scalar(
                select(Mention)
                .where(
                    Mention.project_id == project_id,
                    Mention.source_id == source_id,
                    Mention.content_hash == content_hash,
                )
                .order_by(Mention.ingested_at.asc())
                .limit(1)
            )

    async def list(self, filters: MentionFilters) -> tuple[list[Mention], int]:
        if self.database_manager.using_in_memory_store:
            items = self._apply_filters_in_memory(filters)
            total = len(items)
            paged = items[filters.offset : filters.offset + filters.limit]
            return paged, total

        joined_source, conditions = self._build_sql_conditions(filters)

        statement = select(Mention)
        count_statement = select(func.count()).select_from(Mention)
        if joined_source:
            statement = statement.join(Source, Mention.source_id == Source.id)
            count_statement = count_statement.join(Source, Mention.source_id == Source.id)

        statement = (
            statement.where(*conditions)
            .order_by(Mention.created_at.desc(), Mention.ingested_at.desc())
            .offset(filters.offset)
            .limit(filters.limit)
        )
        count_statement = count_statement.where(*conditions)

        async with self.database_manager.session() as session:
            items = list((await session.scalars(statement)).all())
            total = int((await session.scalar(count_statement)) or 0)
            return items, total

    async def scan(self, filters: MentionFilters | None = None) -> list[Mention]:
        resolved_filters = filters or MentionFilters()
        if self.database_manager.using_in_memory_store:
            return self._apply_filters_in_memory(resolved_filters)

        joined_source, conditions = self._build_sql_conditions(resolved_filters)
        statement = select(Mention)
        if joined_source:
            statement = statement.join(Source, Mention.source_id == Source.id)
        statement = statement.where(*conditions).order_by(Mention.created_at.desc(), Mention.ingested_at.desc())

        async with self.database_manager.session() as session:
            result = await session.scalars(statement)
            return list(result.all())

    def _apply_filters_in_memory(self, filters: MentionFilters) -> list[Mention]:
        items = list(self.database_manager.store.mentions.values())

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
                if (source := self.database_manager.store.sources.get(mention.source_id)) is not None
                and source.type == filters.source_type
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

    @staticmethod
    def _build_sql_conditions(filters: MentionFilters) -> tuple[bool, list]:
        conditions = []
        joined_source = filters.source_type is not None

        if filters.project_id is not None:
            conditions.append(Mention.project_id == filters.project_id)
        if filters.date_from is not None:
            conditions.append(Mention.created_at >= ensure_utc(filters.date_from))
        if filters.date_to is not None:
            conditions.append(Mention.created_at <= ensure_utc(filters.date_to))
        if filters.source_id is not None:
            conditions.append(Mention.source_id == filters.source_id)
        if filters.source_type is not None:
            conditions.append(Source.type == filters.source_type)
        if filters.brand_id is not None:
            conditions.append(Mention.brand_id == filters.brand_id)
        if filters.relevance is not None:
            conditions.append(Mention.relevance_label == filters.relevance)
        if filters.sentiment is not None:
            conditions.append(Mention.sentiment_label == filters.sentiment)
        if filters.criticality is not None:
            conditions.append(Mention.criticality_label == filters.criticality)
        if filters.min_relevance_score is not None:
            conditions.append(Mention.relevance_score >= filters.min_relevance_score)
        if filters.min_sentiment_score is not None:
            conditions.append(Mention.sentiment_score >= filters.min_sentiment_score)
        if filters.duplicates == DuplicateMode.EXCLUDE:
            conditions.append(Mention.is_duplicate.is_(False))
        elif filters.duplicates == DuplicateMode.ONLY:
            conditions.append(Mention.is_duplicate.is_(True))
        if filters.q:
            pattern = f"%{filters.q.strip()}%"
            conditions.append(or_(Mention.title.ilike(pattern), Mention.text.ilike(pattern)))

        return joined_source, conditions
