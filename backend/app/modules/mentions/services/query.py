from __future__ import annotations

import uuid

from app.common.enums import SourceType, relevance_mark
from app.common.pagination import Page
from app.core.exceptions import NotFoundError
from app.modules.brands.repository import BrandRepository
from app.modules.mentions.models import Mention
from app.modules.mentions.repository import MentionRepository
from app.modules.mentions.schemas import (
    MentionBrandDTO,
    MentionFilters,
    MentionMLData,
    MentionRead,
    MentionSourceDTO,
)
from app.modules.sources.repository import SourceRepository


class MentionQueryService:
    def __init__(
        self,
        mention_repository: MentionRepository,
        source_repository: SourceRepository,
        brand_repository: BrandRepository,
    ) -> None:
        self.mention_repository = mention_repository
        self.source_repository = source_repository
        self.brand_repository = brand_repository

    async def list(self, filters: MentionFilters) -> Page[MentionRead]:
        items, total = await self.mention_repository.list(filters)
        dto_items = [await self._to_dto(mention) for mention in items]
        return Page(items=dto_items, total=total, limit=filters.limit, offset=filters.offset)

    async def get(self, mention_id: uuid.UUID) -> MentionRead:
        mention = await self.mention_repository.get(mention_id)
        if mention is None:
            raise NotFoundError(f"Mention '{mention_id}' not found")
        return await self._to_dto(mention)

    async def _to_dto(self, mention: Mention) -> MentionRead:
        source = await self.source_repository.get(mention.source_id)
        brand = await self.brand_repository.get(mention.brand_id) if mention.brand_id else None

        source_dto = MentionSourceDTO(
            id=mention.source_id,
            name=source.name if source is not None else "Unknown source",
            type=source.type if source is not None else SourceType.OTHER,
        )
        brand_dto = None
        if brand is not None:
            brand_dto = MentionBrandDTO(id=brand.id, name=brand.name)

        return MentionRead(
            id=mention.id,
            project_id=mention.project_id,
            brand=brand_dto,
            source=source_dto,
            external_id=mention.external_id,
            title=mention.title,
            text=mention.text,
            raw_url=mention.raw_url,
            created_at=mention.created_at,
            ingested_at=mention.ingested_at,
            is_duplicate=mention.is_duplicate,
            is_duplicate_of=mention.duplicate_of_id,
            ml_data=MentionMLData(
                relevance=mention.relevance_label,
                relevance_mark=relevance_mark(mention.relevance_label),
                relevance_score=mention.relevance_score,
                sentiment=mention.sentiment_label,
                sentiment_score=mention.sentiment_score,
                criticality=mention.criticality_label,
                criticality_score=mention.criticality_score,
                risk_words_hit=list(mention.risk_words_hit),
                cluster_id=mention.cluster_id,
                provider=mention.ml_provider,
                version=mention.ml_version,
            ),
        )
