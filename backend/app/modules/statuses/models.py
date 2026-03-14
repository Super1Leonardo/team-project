from __future__ import annotations

from sqlalchemy import DateTime, Enum as SAEnum, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import ComponentHealthStatus
from app.infra.db.base import Base, UUIDPrimaryKeyMixin


class ComponentStatus(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "component_statuses"

    component_name: Mapped[str] = mapped_column(String(255), nullable=False)
    component_type: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ComponentHealthStatus] = mapped_column(SAEnum(ComponentHealthStatus, native_enum=False), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_seen_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, nullable=False)
