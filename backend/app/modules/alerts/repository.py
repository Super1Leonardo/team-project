from __future__ import annotations

import uuid

from sqlalchemy import select

from app.common.enums import AlertStatus
from app.infra.db.session import DatabaseManager
from app.modules.alerts.models import Alert


class AlertRepository:
    def __init__(self, database_manager: DatabaseManager) -> None:
        self.database_manager = database_manager

    async def add(self, alert: Alert) -> Alert:
        if self.database_manager.using_in_memory_store:
            async with self.database_manager.store.lock:
                self.database_manager.store.alerts[alert.id] = alert
            return alert

        async with self.database_manager.session() as session:
            session.add(alert)
            await session.commit()
            await session.refresh(alert)
            return alert

    async def list(
        self,
        project_id: uuid.UUID | None = None,
        brand_id: uuid.UUID | None = None,
        status: AlertStatus | None = None,
    ) -> list[Alert]:
        if self.database_manager.using_in_memory_store:
            items = list(self.database_manager.store.alerts.values())
            if project_id is not None:
                items = [alert for alert in items if alert.project_id == project_id]
            if brand_id is not None:
                items = [alert for alert in items if alert.brand_id == brand_id]
            if status is not None:
                items = [alert for alert in items if alert.status == status]
            return sorted(items, key=lambda item: item.created_at, reverse=True)

        statement = select(Alert)
        if project_id is not None:
            statement = statement.where(Alert.project_id == project_id)
        if brand_id is not None:
            statement = statement.where(Alert.brand_id == brand_id)
        if status is not None:
            statement = statement.where(Alert.status == status)
        statement = statement.order_by(Alert.created_at.desc())

        async with self.database_manager.session() as session:
            result = await session.scalars(statement)
            return list(result.all())
