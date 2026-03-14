from __future__ import annotations

from sqlalchemy import DateTime, Enum as SAEnum, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import EventLevel
from app.infra.db.base import Base, UUIDPrimaryKeyMixin


class EventLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "event_logs"

    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[EventLevel] = mapped_column(SAEnum(EventLevel, native_enum=False), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_id: Mapped[object | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
