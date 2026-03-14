from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from app.common.enums import (
    AlertStatus,
    AlertType,
    ComponentHealthStatus,
    CriticalityLabel,
    EventLevel,
    RelevanceLabel,
    SentimentLabel,
    SourceType,
)

revision = "20260314_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "brands",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("exceptions", sa.JSON(), nullable=False),
        sa.Column("risk_words", sa.JSON(), nullable=False),
        sa.Column("spike_threshold", sa.Integer(), nullable=False),
        sa.Column("spike_window_minutes", sa.Integer(), nullable=False),
        sa.Column("spike_cooldown_minutes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.Enum(SourceType, native_enum=False), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "mentions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id"), nullable=True),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("raw_url", sa.Text(), nullable=True),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("url_hash", sa.String(length=64), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False),
        sa.Column("duplicate_of_id", sa.Uuid(), sa.ForeignKey("mentions.id"), nullable=True),
        sa.Column("cluster_id", sa.String(length=255), nullable=True),
        sa.Column("relevance_label", sa.Enum(RelevanceLabel, native_enum=False), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("sentiment_label", sa.Enum(SentimentLabel, native_enum=False), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=False),
        sa.Column("criticality_label", sa.Enum(CriticalityLabel, native_enum=False), nullable=False),
        sa.Column("criticality_score", sa.Float(), nullable=False),
        sa.Column("risk_words_hit", sa.JSON(), nullable=False),
        sa.Column("ml_provider", sa.String(length=255), nullable=True),
        sa.Column("ml_version", sa.String(length=255), nullable=True),
        sa.Column("source_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id"), nullable=False),
        sa.Column("type", sa.Enum(AlertType, native_enum=False), nullable=False),
        sa.Column("status", sa.Enum(AlertStatus, native_enum=False), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("window_minutes", sa.Integer(), nullable=False),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False),
        sa.Column("mentions_count", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "event_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("level", sa.Enum(EventLevel, native_enum=False), nullable=False),
        sa.Column("entity_type", sa.String(length=255), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "component_statuses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("component_name", sa.String(length=255), nullable=False),
        sa.Column("component_type", sa.String(length=255), nullable=False),
        sa.Column("status", sa.Enum(ComponentHealthStatus, native_enum=False), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("component_statuses")
    op.drop_table("event_logs")
    op.drop_table("alerts")
    op.drop_table("mentions")
    op.drop_table("sources")
    op.drop_table("brands")
    op.drop_table("projects")
