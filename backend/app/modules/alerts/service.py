from __future__ import annotations

import uuid

from app.common.enums import AlertStatus, AlertType, CriticalityLabel, EventLevel, RelevanceLabel, SentimentLabel
from app.core.constants import EVENT_ALERT_CREATED, EVENT_NOTIFICATION_SENT
from app.core.time import utc_now
from app.infra.redis.client import RedisClient
from app.infra.redis.keys import spike_cooldown_key, spike_counter_key
from app.modules.alerts.models import Alert
from app.modules.alerts.repository import AlertRepository
from app.modules.alerts.schemas import AlertRead
from app.modules.brands.repository import BrandRepository
from app.modules.events.service import EventLogService
from app.modules.mentions.models import Mention
from app.ports.notifier import NotificationPayload, NotifierPort


class AlertService:
    def __init__(
        self,
        repository: AlertRepository,
        brand_repository: BrandRepository,
        redis_client: RedisClient,
        notifier: NotifierPort,
        event_log_service: EventLogService,
    ) -> None:
        self.repository = repository
        self.brand_repository = brand_repository
        self.redis_client = redis_client
        self.notifier = notifier
        self.event_log_service = event_log_service

    async def list(
        self,
        *,
        project_id: uuid.UUID | None = None,
        brand_id: uuid.UUID | None = None,
        status: AlertStatus | None = None,
    ) -> list[AlertRead]:
        alerts = await self.repository.list(project_id=project_id, brand_id=brand_id, status=status)
        items: list[AlertRead] = []
        for alert in alerts:
            brand = await self.brand_repository.get(alert.brand_id)
            items.append(
                AlertRead(
                    id=alert.id,
                    project_id=alert.project_id,
                    brand_id=alert.brand_id,
                    brand_name=brand.name if brand else None,
                    type=alert.type,
                    status=alert.status,
                    threshold=alert.threshold,
                    window_minutes=alert.window_minutes,
                    cooldown_minutes=alert.cooldown_minutes,
                    mentions_count=alert.mentions_count,
                    payload=dict(alert.payload),
                    created_at=alert.created_at,
                )
            )
        return items

    async def process_mention(self, mention: Mention) -> Alert | None:
        if mention.is_duplicate or mention.brand_id is None:
            return None
        if mention.relevance_label != RelevanceLabel.RELEVANT:
            return None
        if not self._qualifies_for_signal(mention):
            return None

        brand = await self.brand_repository.get(mention.brand_id)
        if brand is None:
            return None

        counter_key = spike_counter_key(
            mention.project_id,
            mention.brand_id,
            mention.ingested_at,
            brand.spike_window_minutes,
        )
        mentions_count = await self.redis_client.incr(counter_key)
        if mentions_count == 1:
            await self.redis_client.expire(counter_key, brand.spike_window_minutes * 60)

        cooldown_key = spike_cooldown_key(mention.project_id, mention.brand_id)
        if mentions_count < brand.spike_threshold or await self.redis_client.exists(cooldown_key):
            return None

        alert = Alert(
            id=uuid.uuid4(),
            project_id=mention.project_id,
            brand_id=mention.brand_id,
            type=AlertType.SPIKE_NEGATIVE,
            status=AlertStatus.OPEN,
            threshold=brand.spike_threshold,
            window_minutes=brand.spike_window_minutes,
            cooldown_minutes=brand.spike_cooldown_minutes,
            mentions_count=mentions_count,
            payload={
                "mention_id": str(mention.id),
                "raw_url": mention.raw_url,
                "risk_words_hit": list(mention.risk_words_hit),
                "criticality": mention.criticality_label.value,
            },
            created_at=utc_now(),
        )
        saved = await self.repository.add(alert)
        await self.redis_client.set(cooldown_key, str(saved.id), ex=brand.spike_cooldown_minutes * 60, nx=True)

        await self.event_log_service.record(
            EVENT_ALERT_CREATED,
            "alert",
            entity_id=saved.id,
            level=EventLevel.WARNING,
            payload={
                "brand_id": str(saved.brand_id),
                "mentions_count": saved.mentions_count,
                "threshold": saved.threshold,
            },
        )

        try:
            notification_result = await self.notifier.send(
                NotificationPayload(
                    alert_id=saved.id,
                    project_id=saved.project_id,
                    brand_id=saved.brand_id,
                    brand_name=brand.name,
                    alert_type=saved.type.value,
                    mentions_count=saved.mentions_count,
                    payload=dict(saved.payload),
                )
            )
            await self.event_log_service.record(
                EVENT_NOTIFICATION_SENT,
                "alert",
                entity_id=saved.id,
                level=EventLevel.INFO if notification_result.delivered else EventLevel.WARNING,
                payload={
                    "provider": notification_result.provider,
                    "detail": notification_result.detail,
                    "delivered": notification_result.delivered,
                },
            )
        except Exception as exc:
            await self.event_log_service.record(
                EVENT_NOTIFICATION_SENT,
                "alert",
                entity_id=saved.id,
                level=EventLevel.WARNING,
                payload={"provider": "notifier", "detail": str(exc), "delivered": False},
            )
        return saved

    @staticmethod
    def _qualifies_for_signal(mention: Mention) -> bool:
        return (
            mention.sentiment_label == SentimentLabel.NEGATIVE
            or bool(mention.risk_words_hit)
            or mention.criticality_label in {CriticalityLabel.HIGH, CriticalityLabel.CRITICAL}
        )
