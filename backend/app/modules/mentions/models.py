from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import CriticalityLabel, RelevanceLabel, SentimentLabel
from app.infra.db.base import Base, UUIDPrimaryKeyMixin


class Mention(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "mentions"

    project_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    brand_id: Mapped[object | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("brands.id"), nullable=True)
    source_id: Mapped[object] = mapped_column(Uuid(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    url_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False)
    duplicate_of_id: Mapped[object | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("mentions.id"), nullable=True)
    cluster_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    relevance_label: Mapped[RelevanceLabel] = mapped_column(SAEnum(RelevanceLabel, native_enum=False), nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    sentiment_label: Mapped[SentimentLabel] = mapped_column(SAEnum(SentimentLabel, native_enum=False), nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    criticality_label: Mapped[CriticalityLabel] = mapped_column(SAEnum(CriticalityLabel, native_enum=False), nullable=False)
    criticality_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_words_hit: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    ml_provider: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ml_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_metadata: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
