from __future__ import annotations

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import AlertStatus, AlertType
from app.infra.db.base import Base, UUIDPrimaryKeyMixin


class Alert(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "alerts"

    project_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    brand_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), ForeignKey("brands.id"), nullable=False)
    type: Mapped[AlertType] = mapped_column(SAEnum(AlertType, native_enum=False), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(SAEnum(AlertStatus, native_enum=False), nullable=False)
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    window_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    mentions_count: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
