from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.db.base import Base, UUIDPrimaryKeyMixin


class Brand(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "brands"

    project_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    exceptions: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    risk_words: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    spike_threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    spike_window_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    spike_cooldown_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
