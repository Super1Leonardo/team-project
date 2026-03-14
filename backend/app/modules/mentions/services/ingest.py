from __future__ import annotations

import uuid

from app.common.enums import EventLevel
from app.common.types import combine_title_text, normalize_text
from app.core.constants import (
    EVENT_DUPLICATE_DETECTED,
    EVENT_MENTION_INGESTED,
    EVENT_ML_FAILED,
    EVENT_ML_UNAVAILABLE,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.core.time import ensure_utc, utc_now
from app.modules.alerts.service import AlertService
from app.modules.brands.repository import BrandRepository
from app.modules.events.service import EventLogService
from app.modules.mentions.models import Mention
from app.modules.mentions.repository import MentionRepository
from app.modules.mentions.schemas import MentionIngestRequest
from app.modules.mentions.services.brand_match import BrandMatchService
from app.modules.mentions.services.dedup import DeduplicationService
from app.modules.sources.repository import SourceRepository
from app.ports.ml import MLPort, MLRequest


class MentionIngestService:
    def __init__(
        self,
        source_repository: SourceRepository,
        brand_repository: BrandRepository,
        mention_repository: MentionRepository,
        event_log_service: EventLogService,
        brand_match_service: BrandMatchService,
        deduplication_service: DeduplicationService,
        ml_gateway: MLPort,
        alert_service: AlertService,
    ) -> None:
        self.source_repository = source_repository
        self.brand_repository = brand_repository
        self.mention_repository = mention_repository
        self.event_log_service = event_log_service
        self.brand_match_service = brand_match_service
        self.deduplication_service = deduplication_service
        self.ml_gateway = ml_gateway
        self.alert_service = alert_service

    async def ingest(self, payload: MentionIngestRequest) -> Mention:
        source = await self.source_repository.get_by_identifier(payload.source_id)
        if source is None:
            raise NotFoundError(f"Source '{payload.source_id}' not found")

        created_at = ensure_utc(payload.created_at)
        if created_at is None:
            raise ValidationError("created_at must be provided")

        title = (payload.title or "").strip()
        text = (payload.text or "").strip()
        if not title:
            title = text[:120] or "Untitled mention"
        if not text:
            text = title

        normalized_text = normalize_text(combine_title_text(title, text))
        brands = await self.brand_repository.list_by_project(source.project_id)
        brand_match = self.brand_match_service.match(brands, title, text)

        dedup_result = await self.deduplication_service.detect(
            source.project_id,
            source.id,
            title=title,
            text=text,
            raw_url=payload.raw_url,
        )

        ml_result = await self.ml_gateway.predict(
            MLRequest(
                project_id=source.project_id,
                source_id=source.id,
                title=title,
                text=text,
                normalized_text=normalized_text,
                rule_relevance_label=brand_match.relevance_label,
                risk_words_hit=brand_match.risk_words_hit,
                metadata={"content_hash": dedup_result.content_hash},
            )
        )

        if ml_result.used_fallback:
            await self.event_log_service.record(
                EVENT_ML_FAILED if ml_result.failure_reason else EVENT_ML_UNAVAILABLE,
                "mention",
                level=EventLevel.WARNING,
                payload={
                    "source_id": str(source.id),
                    "reason": ml_result.failure_reason,
                },
            )

        prediction = ml_result.prediction
        risk_words_hit = sorted(set(brand_match.risk_words_hit + prediction.risk_words_hit))
        ingested_at = utc_now()

        mention = Mention(
            id=uuid.uuid4(),
            project_id=source.project_id,
            brand_id=brand_match.brand.id if brand_match.brand else None,
            source_id=source.id,
            external_id=(payload.external_id or "").strip() or None,
            title=title,
            text=text,
            raw_url=(payload.raw_url or "").strip() or None,
            normalized_text=normalized_text,
            url_hash=dedup_result.url_hash,
            content_hash=dedup_result.content_hash,
            is_duplicate=dedup_result.is_duplicate,
            duplicate_of_id=dedup_result.duplicate_of_id,
            cluster_id=dedup_result.cluster_id or prediction.cluster_id,
            relevance_label=prediction.relevance_label,
            relevance_score=prediction.relevance_score,
            sentiment_label=prediction.sentiment_label,
            sentiment_score=prediction.sentiment_score,
            criticality_label=prediction.criticality_label,
            criticality_score=prediction.criticality_score,
            risk_words_hit=risk_words_hit,
            ml_provider=prediction.provider,
            ml_version=prediction.version,
            source_metadata=payload.metadata.model_dump(exclude_none=True),
            created_at=created_at,
            ingested_at=ingested_at,
        )
        saved = await self.mention_repository.add(mention)

        if saved.is_duplicate:
            await self.event_log_service.record(
                EVENT_DUPLICATE_DETECTED,
                "mention",
                entity_id=saved.id,
                payload={
                    "duplicate_of_id": str(saved.duplicate_of_id),
                    "reason": dedup_result.duplicate_reason,
                },
            )

        await self.event_log_service.record(
            EVENT_MENTION_INGESTED,
            "mention",
            entity_id=saved.id,
            payload={
                "project_id": str(saved.project_id),
                "source_id": str(saved.source_id),
                "brand_id": str(saved.brand_id) if saved.brand_id else None,
                "is_duplicate": saved.is_duplicate,
            },
        )

        await self.alert_service.process_mention(saved)
        return saved
