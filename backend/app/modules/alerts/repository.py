from __future__ import annotations

import uuid

from app.common.enums import AlertStatus
from app.infra.db.session import InMemoryStore
from app.modules.alerts.models import Alert


class AlertRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    async def add(self, alert: Alert) -> Alert:
        async with self.store.lock:
            self.store.alerts[alert.id] = alert
        return alert

    async def list(
        self,
        project_id: uuid.UUID | None = None,
        brand_id: uuid.UUID | None = None,
        status: AlertStatus | None = None,
    ) -> list[Alert]:
        items = list(self.store.alerts.values())
        if project_id is not None:
            items = [alert for alert in items if alert.project_id == project_id]
        if brand_id is not None:
            items = [alert for alert in items if alert.brand_id == brand_id]
        if status is not None:
            items = [alert for alert in items if alert.status == status]
        return sorted(items, key=lambda item: item.created_at, reverse=True)
