from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import SourceType
from app.infra.db.base import Base, UUIDPrimaryKeyMixin


class Source(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "sources"

    project_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[SourceType] = mapped_column(SAEnum(SourceType, native_enum=False), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    last_collected_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
