from __future__ import annotations

import uuid

import pytest

from app.common.enums import CriticalityLabel, RelevanceLabel, SentimentLabel
from app.core.config import Settings
from app.core.time import utc_now
from app.infra.db.session import DatabaseManager
from app.infra.gateways.health_gateway import ExternalHealthGateway
from app.infra.gateways.notifier_gateway import NotifierGateway
from app.infra.redis.client import build_redis_client
from app.modules.alerts.models import Alert
from app.modules.alerts.repository import AlertRepository
from app.modules.alerts.service import AlertService
from app.modules.brands.models import Brand
from app.modules.brands.repository import BrandRepository
from app.modules.events.repository import EventLogRepository
from app.modules.events.service import EventLogService
from app.modules.mentions.models import Mention


def make_brand(project_id: uuid.UUID, *, threshold: int = 2, cooldown: int = 60) -> Brand:
    now = utc_now()
    return Brand(
        id=uuid.uuid4(),
        project_id=project_id,
        name="Acme",
        keywords=["acme"],
        exceptions=[],
        risk_words=["сбой"],
        spike_threshold=threshold,
        spike_window_minutes=60,
        spike_cooldown_minutes=cooldown,
        created_at=now,
        updated_at=now,
    )


def make_mention(
    project_id: uuid.UUID,
    brand_id: uuid.UUID,
    *,
    relevance: RelevanceLabel,
    sentiment: SentimentLabel,
    criticality: CriticalityLabel = CriticalityLabel.LOW,
    risk_words_hit: list[str] | None = None,
) -> Mention:
    now = utc_now()
    return Mention(
        id=uuid.uuid4(),
        project_id=project_id,
        brand_id=brand_id,
        source_id=uuid.uuid4(),
        external_id=None,
        title="Acme пост",
        text="Описание",
        raw_url=f"https://example.com/{uuid.uuid4()}",
        normalized_text="acme post",
        url_hash=None,
        content_hash=str(uuid.uuid4()),
        is_duplicate=False,
        duplicate_of_id=None,
        cluster_id=None,
        relevance_label=relevance,
        relevance_score=0.9,
        sentiment_label=sentiment,
        sentiment_score=0.9,
        criticality_label=criticality,
        criticality_score=0.9,
        risk_words_hit=risk_words_hit or [],
        ml_provider="test",
        ml_version="v1",
        source_metadata={},
        created_at=now,
        ingested_at=now,
    )


@pytest.mark.asyncio
async def test_irrelevant_mention_does_not_create_alert() -> None:
    project_id = uuid.uuid4()
    settings = Settings(
        database_url=None,
        redis_url=None,
        ml_service_url=None,
        collector_service_url=None,
        notifier_webhook_url=None,
    )
    database_manager = DatabaseManager(settings)
    brand_repository = BrandRepository(database_manager)
    alert_repository = AlertRepository(database_manager)
    event_log_service = EventLogService(EventLogRepository(database_manager))
    redis_client = build_redis_client(settings)
    notifier = NotifierGateway(settings, ExternalHealthGateway(1.0))
    service = AlertService(alert_repository, brand_repository, redis_client, notifier, event_log_service)

    brand = make_brand(project_id, threshold=1)
    await brand_repository.add(brand)
    mention = make_mention(
        project_id,
        brand.id,
        relevance=RelevanceLabel.IRRELEVANT,
        sentiment=SentimentLabel.NEGATIVE,
        risk_words_hit=["сбой"],
    )

    alert = await service.process_mention(mention)

    assert alert is None
    assert await alert_repository.list() == []


@pytest.mark.asyncio
async def test_negative_relevant_mentions_trigger_once_and_cooldown_blocks_next() -> None:
    project_id = uuid.uuid4()
    settings = Settings(
        database_url=None,
        redis_url=None,
        ml_service_url=None,
        collector_service_url=None,
        notifier_webhook_url=None,
    )
    database_manager = DatabaseManager(settings)
    brand_repository = BrandRepository(database_manager)
    alert_repository = AlertRepository(database_manager)
    event_log_service = EventLogService(EventLogRepository(database_manager))
    redis_client = build_redis_client(settings)
    notifier = NotifierGateway(settings, ExternalHealthGateway(1.0))
    service = AlertService(alert_repository, brand_repository, redis_client, notifier, event_log_service)

    brand = make_brand(project_id, threshold=2, cooldown=120)
    await brand_repository.add(brand)

    mention1 = make_mention(
        project_id,
        brand.id,
        relevance=RelevanceLabel.RELEVANT,
        sentiment=SentimentLabel.NEGATIVE,
        criticality=CriticalityLabel.HIGH,
        risk_words_hit=["сбой"],
    )
    mention2 = make_mention(
        project_id,
        brand.id,
        relevance=RelevanceLabel.RELEVANT,
        sentiment=SentimentLabel.NEGATIVE,
        criticality=CriticalityLabel.HIGH,
        risk_words_hit=["сбой"],
    )
    mention3 = make_mention(
        project_id,
        brand.id,
        relevance=RelevanceLabel.RELEVANT,
        sentiment=SentimentLabel.NEGATIVE,
        criticality=CriticalityLabel.HIGH,
        risk_words_hit=["сбой"],
    )

    assert await service.process_mention(mention1) is None
    alert = await service.process_mention(mention2)
    assert isinstance(alert, Alert)
    assert await service.process_mention(mention3) is None
    assert len(await alert_repository.list()) == 1
