from __future__ import annotations

import uuid

import pytest

from app.common.enums import CriticalityLabel, RelevanceLabel, SentimentLabel
from app.common.types import normalize_url, sha256_hex
from app.core.config import Settings
from app.core.time import utc_now
from app.infra.db.session import DatabaseManager
from app.modules.mentions.models import Mention
from app.modules.mentions.repository import MentionRepository
from app.modules.mentions.services.dedup import DeduplicationService


def make_mention(*, project_id: uuid.UUID, source_id: uuid.UUID, title: str, text: str, raw_url: str | None) -> Mention:
    now = utc_now()
    normalized_url = normalize_url(raw_url)
    return Mention(
        id=uuid.uuid4(),
        project_id=project_id,
        brand_id=None,
        source_id=source_id,
        external_id=None,
        title=title,
        text=text,
        raw_url=raw_url,
        normalized_text=f"{title} {text}".lower(),
        url_hash=sha256_hex(normalized_url) if normalized_url else None,
        content_hash=sha256_hex(f"{title.lower()} {text.lower()}"),
        is_duplicate=False,
        duplicate_of_id=None,
        cluster_id=None,
        relevance_label=RelevanceLabel.REVIEW,
        relevance_score=0.5,
        sentiment_label=SentimentLabel.NEUTRAL,
        sentiment_score=0.5,
        criticality_label=CriticalityLabel.LOW,
        criticality_score=0.4,
        risk_words_hit=[],
        ml_provider="test",
        ml_version="v1",
        source_metadata={},
        created_at=now,
        ingested_at=now,
    )


@pytest.mark.asyncio
async def test_dedup_detects_hard_duplicate_by_url() -> None:
    database_manager = DatabaseManager(Settings(database_url=None))
    repository = MentionRepository(database_manager)
    service = DeduplicationService(repository)
    project_id = uuid.uuid4()
    source_id = uuid.uuid4()

    existing = make_mention(
        project_id=project_id,
        source_id=source_id,
        title="Первый пост",
        text="Описание",
        raw_url="https://example.com/post/1?a=1&b=2",
    )
    await repository.add(existing)

    result = await service.detect(
        project_id,
        source_id,
        title="Другой заголовок",
        text="Другой текст",
        raw_url="https://example.com/post/1?b=2&a=1#fragment",
    )

    assert result.is_duplicate is True
    assert result.duplicate_of_id == existing.id
    assert result.duplicate_reason == "url_hash"


@pytest.mark.asyncio
async def test_dedup_detects_content_duplicate_when_url_changes() -> None:
    database_manager = DatabaseManager(Settings(database_url=None))
    repository = MentionRepository(database_manager)
    service = DeduplicationService(repository)
    project_id = uuid.uuid4()
    source_id = uuid.uuid4()

    existing = make_mention(
        project_id=project_id,
        source_id=source_id,
        title="Acme outage",
        text="Service down for all users",
        raw_url="https://example.com/post/1",
    )
    await repository.add(existing)

    result = await service.detect(
        project_id,
        source_id,
        title="Acme outage",
        text="Service down for all users",
        raw_url="https://mirror.example.com/post/other",
    )

    assert result.is_duplicate is True
    assert result.duplicate_of_id == existing.id
    assert result.duplicate_reason == "content_hash"
