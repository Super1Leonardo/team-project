from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from datetime import timedelta
from typing import Any
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from backend.app.common.schemas import ParsedMessage
from backend.app.core.config import Settings
from backend.app.core.exceptions import DomainValidationError, ResourceNotFoundError

SUPPORTED_SOURCE_TYPES = ("telegram", "vk", "dzen", "rss", "website")
WEBSITE_SELECTOR_KEYS = (
    "article_selector",
    "link_selector",
    "summary_selector",
    "date_selector",
    "site_title_selector",
    "detail_title_selector",
    "detail_paragraph_selector",
    "original_link_selector",
)
DEFAULT_BOOTSTRAP_PROJECT = {
    "name": "Brand Radar",
    "keywords": [],
    "exclude_keywords": [],
    "risk_words": [],
}
DEFAULT_BOOTSTRAP_SOURCES = (
    {
        "source_type": "telegram",
        "source_config": {"channel": "https://t.me/brand_radar_case"},
        "is_active": True,
        "poll_interval_s": 300,
    },
    {
        "source_type": "website",
        "source_config": {"url": "http://web-brandradar.ingress.prodcontest.com/"},
        "is_active": True,
        "poll_interval_s": 300,
    },
    {
        "source_type": "rss",
        "source_config": {
            "url": "http://rss-brandradar.ingress.prodcontest.com/rss.xml"
        },
        "is_active": True,
        "poll_interval_s": 300,
    },
)
LEGACY_BOOTSTRAP_RSS_URL = "http://rss-brandradar.ingress.prodcontest.com/"


class BrandRadarPostgresStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    def init_db(self, retries: int = 10, delay_seconds: float = 1.0) -> None:
        last_error: Exception | None = None

        for attempt in range(retries):
            try:
                with self._connect() as conn, conn.cursor() as cur:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS projects (
                            id SERIAL PRIMARY KEY,
                            name TEXT NOT NULL,
                            keywords TEXT[] NOT NULL,
                            exclude_keywords TEXT[] NOT NULL DEFAULT '{}',
                            risk_words TEXT[] NOT NULL DEFAULT '{}',
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS sources (
                            id SERIAL PRIMARY KEY,
                            project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                            source_type TEXT NOT NULL,
                            source_config JSONB NOT NULL,
                            is_active BOOLEAN NOT NULL DEFAULT TRUE,
                            poll_interval_s INT NOT NULL DEFAULT 60,
                            last_collected_at TIMESTAMPTZ,
                            last_error TEXT,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            CHECK (source_type IN ('telegram', 'vk', 'dzen', 'rss', 'website')),
                            CHECK (poll_interval_s > 0)
                        )
                        """
                    )
                    cur.execute(
                        """
                        ALTER TABLE sources
                        DROP CONSTRAINT IF EXISTS sources_source_type_check
                        """
                    )
                    cur.execute(
                        """
                        ALTER TABLE sources
                        ADD CONSTRAINT sources_source_type_check
                        CHECK (source_type IN ('telegram', 'vk', 'dzen', 'rss', 'website'))
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS raw_posts (
                            id BIGSERIAL PRIMARY KEY,
                            source_id INT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
                            external_id TEXT NOT NULL,
                            url TEXT,
                            title TEXT,
                            text TEXT NOT NULL,
                            author TEXT,
                            published_at TIMESTAMPTZ NOT NULL,
                            collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            raw_meta JSONB NOT NULL DEFAULT '{}',
                            ml_processed BOOLEAN NOT NULL DEFAULT FALSE,
                            ml_failed_at TIMESTAMPTZ,
                            ml_error TEXT,
                            UNIQUE (source_id, external_id)
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS dedup_groups (
                            id BIGSERIAL PRIMARY KEY,
                            project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                            representative_mention_id BIGINT,
                            mention_count INT NOT NULL DEFAULT 1,
                            centroid_embedding VECTOR(384),
                            first_seen_at TIMESTAMPTZ,
                            last_seen_at TIMESTAMPTZ,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS mentions (
                            id BIGSERIAL PRIMARY KEY,
                            raw_post_id BIGINT NOT NULL UNIQUE REFERENCES raw_posts(id) ON DELETE CASCADE,
                            project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                            relevance_score DOUBLE PRECISION NOT NULL,
                            relevance_label TEXT NOT NULL,
                            sentiment_score DOUBLE PRECISION NOT NULL,
                            sentiment_label TEXT NOT NULL,
                            has_risk_words BOOLEAN NOT NULL DEFAULT FALSE,
                            embedding VECTOR(384),
                            dedup_group_id BIGINT REFERENCES dedup_groups(id) ON DELETE SET NULL,
                            is_primary BOOLEAN NOT NULL DEFAULT TRUE,
                            resolved BOOLEAN NOT NULL DEFAULT FALSE,
                            processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            clickhouse_synced_at TIMESTAMPTZ
                        )
                        """
                    )
                    cur.execute(
                        """
                        ALTER TABLE raw_posts
                        ADD COLUMN IF NOT EXISTS ml_failed_at TIMESTAMPTZ
                        """
                    )
                    cur.execute(
                        """
                        ALTER TABLE raw_posts
                        ADD COLUMN IF NOT EXISTS ml_error TEXT
                        """
                    )
                    cur.execute(
                        """
                        ALTER TABLE mentions
                        ADD COLUMN IF NOT EXISTS clickhouse_synced_at TIMESTAMPTZ
                        """
                    )
                    cur.execute(
                        """
                        ALTER TABLE mentions
                        ADD COLUMN IF NOT EXISTS resolved BOOLEAN NOT NULL DEFAULT FALSE
                        """
                    )
                    cur.execute(
                        """
                        ALTER TABLE dedup_groups
                        ADD COLUMN IF NOT EXISTS centroid_embedding VECTOR(384)
                        """
                    )
                    cur.execute(
                        """
                        ALTER TABLE dedup_groups
                        ADD COLUMN IF NOT EXISTS first_seen_at TIMESTAMPTZ
                        """
                    )
                    cur.execute(
                        """
                        ALTER TABLE dedup_groups
                        ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ
                        """
                    )
                    cur.execute(
                        """
                        ALTER TABLE mentions
                        ALTER COLUMN embedding DROP NOT NULL
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS events (
                            id BIGSERIAL PRIMARY KEY,
                            project_id INT,
                            event_type TEXT NOT NULL,
                            payload JSONB NOT NULL DEFAULT '{}',
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_raw_posts_unprocessed
                        ON raw_posts (ml_processed)
                        WHERE NOT ml_processed
                        """
                    )
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_raw_posts_ml_queue
                        ON raw_posts (collected_at ASC, id ASC)
                        WHERE ml_processed = FALSE AND ml_failed_at IS NULL
                        """
                    )
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_raw_posts_source_published
                        ON raw_posts (source_id, published_at DESC)
                        """
                    )
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_raw_posts_published
                        ON raw_posts (published_at DESC, id DESC)
                        """
                    )
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_mentions_embedding
                        ON mentions
                        USING ivfflat (embedding vector_cosine_ops)
                        WITH (lists = 100)
                        """
                    )
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_dedup_groups_centroid_embedding
                        ON dedup_groups
                        USING ivfflat (centroid_embedding vector_cosine_ops)
                        WITH (lists = 100)
                        """
                    )
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_mentions_feed
                        ON mentions (project_id, processed_at DESC)
                        WHERE relevance_label = 'relevant' AND is_primary = TRUE
                        """
                    )
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_mentions_project_processed
                        ON mentions (project_id, processed_at DESC)
                        """
                    )
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_mentions_feed_sentiment
                        ON mentions (project_id, sentiment_label, processed_at DESC)
                        WHERE relevance_label = 'relevant' AND is_primary = TRUE
                        """
                    )
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_mentions_clickhouse_pending
                        ON mentions (processed_at ASC, id ASC)
                        WHERE clickhouse_synced_at IS NULL
                        """
                    )
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_events_lookup
                        ON events (project_id, created_at DESC)
                        """
                    )
                self.bootstrap_default_project_and_sources()
                return
            except psycopg.OperationalError as exc:
                last_error = exc
                if attempt == retries - 1:
                    break
                time.sleep(delay_seconds)

        if last_error is not None:
            raise last_error

    def bootstrap_default_project_and_sources(self) -> None:
        with self._connect(autocommit=False) as conn, conn.cursor() as cur:
            project_id, project_created = self._ensure_bootstrap_project(cur)
            inserted_sources, updated_sources = self._ensure_bootstrap_sources(
                cur, project_id
            )
            if project_created or inserted_sources > 0 or updated_sources > 0:
                conn.commit()

    def _ensure_bootstrap_project(self, cur: psycopg.Cursor) -> tuple[int, bool]:
        cur.execute(
            """
            SELECT id
            FROM projects
            WHERE name = %s
            ORDER BY id ASC
            LIMIT 1
            """,
            (DEFAULT_BOOTSTRAP_PROJECT["name"],),
        )
        project_row = cur.fetchone()
        if project_row is not None:
            return int(project_row["id"]), False

        cur.execute(
            """
            INSERT INTO projects (
                name,
                keywords,
                exclude_keywords,
                risk_words
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (
                DEFAULT_BOOTSTRAP_PROJECT["name"],
                DEFAULT_BOOTSTRAP_PROJECT["keywords"],
                DEFAULT_BOOTSTRAP_PROJECT["exclude_keywords"],
                DEFAULT_BOOTSTRAP_PROJECT["risk_words"],
            ),
        )
        project_row = cur.fetchone()
        if project_row is None:
            raise RuntimeError("Failed to create bootstrap project.")
        return int(project_row["id"]), True

    def _ensure_bootstrap_sources(
        self, cur: psycopg.Cursor, project_id: int
    ) -> tuple[int, int]:
        cur.execute(
            """
            SELECT id, source_type, source_config
            FROM sources
            WHERE project_id = %s
            ORDER BY id ASC
            """,
            (project_id,),
        )
        existing_rows = list(cur.fetchall())
        updated_sources = 0
        existing_sources: set[tuple[str, str]] = set()
        bootstrap_source_keys = self._bootstrap_source_keys()
        canonical_source_ids: dict[tuple[str, str], int] = {}
        duplicate_source_ids: list[tuple[int, int]] = []

        for row in existing_rows:
            normalized_existing_config = self._normalize_source_config(
                row["source_type"],
                row["source_config"],
            )
            if normalized_existing_config != row["source_config"]:
                cur.execute(
                    """
                    UPDATE sources
                    SET source_config = %s
                    WHERE id = %s
                    """,
                    (Jsonb(normalized_existing_config), row["id"]),
                )
                updated_sources += 1

            source_key = (
                row["source_type"],
                self._source_config_key(normalized_existing_config),
            )
            if (
                source_key in bootstrap_source_keys
                and source_key in canonical_source_ids
            ):
                duplicate_source_ids.append(
                    (int(row["id"]), canonical_source_ids[source_key])
                )
                continue

            canonical_source_ids[source_key] = int(row["id"])
            existing_sources.add(source_key)

        for duplicate_source_id, canonical_source_id in duplicate_source_ids:
            self._merge_source_into_existing_source(
                cur,
                source_id=duplicate_source_id,
                canonical_source_id=canonical_source_id,
            )
            updated_sources += 1

        inserted_sources = 0

        for source in DEFAULT_BOOTSTRAP_SOURCES:
            normalized_source_config = self._normalize_source_config(
                source["source_type"],
                source["source_config"],
            )
            source_key = (
                source["source_type"],
                self._source_config_key(normalized_source_config),
            )
            if source_key in existing_sources:
                continue
            cur.execute(
                """
                INSERT INTO sources (
                    project_id,
                    source_type,
                    source_config,
                    is_active,
                    poll_interval_s
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    project_id,
                    source["source_type"],
                    Jsonb(normalized_source_config),
                    source["is_active"],
                    source["poll_interval_s"],
                ),
            )
            existing_sources.add(source_key)
            inserted_sources += 1

        return inserted_sources, updated_sources

    @staticmethod
    def _bootstrap_source_keys() -> set[tuple[str, str]]:
        return {
            (
                source["source_type"],
                BrandRadarPostgresStore._source_config_key(
                    BrandRadarPostgresStore._normalize_source_config(
                        source["source_type"],
                        source["source_config"],
                    )
                ),
            )
            for source in DEFAULT_BOOTSTRAP_SOURCES
        }

    def _merge_source_into_existing_source(
        self,
        cur: psycopg.Cursor,
        *,
        source_id: int,
        canonical_source_id: int,
    ) -> None:
        cur.execute(
            """
            UPDATE raw_posts rp
            SET source_id = %s
            WHERE rp.source_id = %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM raw_posts existing
                  WHERE existing.source_id = %s
                    AND existing.external_id = rp.external_id
              )
            """,
            (canonical_source_id, source_id, canonical_source_id),
        )
        cur.execute(
            """
            DELETE FROM raw_posts
            WHERE source_id = %s
            """,
            (source_id,),
        )
        cur.execute(
            """
            DELETE FROM sources
            WHERE id = %s
            """,
            (source_id,),
        )

    def ping(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")

    def create_project(
        self,
        name: str,
        keywords: list[str],
        exclude_keywords: list[str] | None = None,
        risk_words: list[str] | None = None,
    ) -> dict[str, Any]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO projects (
                    name,
                    keywords,
                    exclude_keywords,
                    risk_words
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id, name, keywords, exclude_keywords, risk_words, created_at
                """,
                (
                    name,
                    keywords,
                    exclude_keywords or [],
                    risk_words or [],
                ),
            )
            row = cur.fetchone()

        return dict(row)

    def list_projects(self) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.keywords,
                    p.exclude_keywords,
                    p.risk_words,
                    p.created_at,
                    (
                        SELECT COUNT(*)
                        FROM sources s
                        WHERE s.project_id = p.id
                    ) AS sources_count,
                    (
                        SELECT COUNT(*)
                        FROM mentions m
                        WHERE m.project_id = p.id
                    ) AS mentions_count
                FROM projects p
                ORDER BY
                    CASE WHEN p.name = %s THEN 0 ELSE 1 END,
                    p.created_at DESC,
                    p.id DESC
                """,
                (DEFAULT_BOOTSTRAP_PROJECT["name"],),
            )
            rows = cur.fetchall()

        return [dict(row) for row in rows]

    def get_project(self, project_id: int) -> dict[str, Any]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.keywords,
                    p.exclude_keywords,
                    p.risk_words,
                    p.created_at,
                    (
                        SELECT COUNT(*)
                        FROM sources s
                        WHERE s.project_id = p.id
                    ) AS sources_count,
                    (
                        SELECT COUNT(*)
                        FROM mentions m
                        WHERE m.project_id = p.id
                    ) AS mentions_count
                FROM projects p
                WHERE p.id = %s
                """,
                (project_id,),
            )
            row = cur.fetchone()

        if row is None:
            raise ResourceNotFoundError(f"Project {project_id} was not found.")
        return dict(row)

    def get_preferred_project(self) -> dict[str, Any]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.keywords,
                    p.exclude_keywords,
                    p.risk_words,
                    p.created_at
                FROM projects p
                ORDER BY
                    CASE WHEN p.name = %s THEN 0 ELSE 1 END,
                    p.created_at DESC,
                    p.id DESC
                LIMIT 1
                """,
                (DEFAULT_BOOTSTRAP_PROJECT["name"],),
            )
            row = cur.fetchone()

        if row is None:
            raise ResourceNotFoundError("No projects were found.")
        return dict(row)

    def update_project(
        self,
        project_id: int,
        *,
        name: str | None = None,
        keywords: list[str] | None = None,
        exclude_keywords: list[str] | None = None,
        risk_words: list[str] | None = None,
    ) -> dict[str, Any]:
        project = self.get_project(project_id)

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE projects
                SET
                    name = %s,
                    keywords = %s,
                    exclude_keywords = %s,
                    risk_words = %s
                WHERE id = %s
                """,
                (
                    name if name is not None else project["name"],
                    keywords if keywords is not None else project["keywords"],
                    (
                        exclude_keywords
                        if exclude_keywords is not None
                        else project["exclude_keywords"]
                    ),
                    risk_words if risk_words is not None else project["risk_words"],
                    project_id,
                ),
            )

        return self.get_project(project_id)

    def reset_project_mentions_for_reprocessing(
        self, project_id: int
    ) -> dict[str, int]:
        self._ensure_project_exists(project_id)

        with self._connect(autocommit=False) as conn, conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM mentions
                WHERE project_id = %s
                """,
                (project_id,),
            )
            deleted_mentions = int(cur.rowcount or 0)

            cur.execute(
                """
                DELETE FROM dedup_groups
                WHERE project_id = %s
                """,
                (project_id,),
            )
            deleted_groups = int(cur.rowcount or 0)

            cur.execute(
                """
                UPDATE raw_posts AS rp
                SET ml_processed = FALSE,
                    ml_failed_at = NULL,
                    ml_error = NULL
                FROM sources s
                WHERE s.id = rp.source_id
                  AND s.project_id = %s
                """,
                (project_id,),
            )
            requeued_raw_posts = int(cur.rowcount or 0)

            self._insert_event(
                cur,
                project_id=project_id,
                event_type="project_mentions_requeued",
                payload={
                    "mentions_deleted": deleted_mentions,
                    "dedup_groups_deleted": deleted_groups,
                    "raw_posts_requeued": requeued_raw_posts,
                },
            )
            conn.commit()

        return {
            "mentions_deleted": deleted_mentions,
            "dedup_groups_deleted": deleted_groups,
            "raw_posts_requeued": requeued_raw_posts,
        }

    def requeue_failed_raw_posts_for_reprocessing(self, project_id: int) -> int:
        self._ensure_project_exists(project_id)

        with self._connect(autocommit=False) as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE raw_posts AS rp
                SET ml_processed = FALSE,
                    ml_failed_at = NULL,
                    ml_error = NULL
                FROM sources s
                WHERE s.id = rp.source_id
                  AND s.project_id = %s
                  AND rp.ml_processed = FALSE
                  AND rp.ml_failed_at IS NOT NULL
                """,
                (project_id,),
            )
            requeued_raw_posts = int(cur.rowcount or 0)

            if requeued_raw_posts > 0:
                self._insert_event(
                    cur,
                    project_id=project_id,
                    event_type="project_failed_raw_posts_requeued",
                    payload={
                        "raw_posts_requeued": requeued_raw_posts,
                    },
                )
            conn.commit()

        return requeued_raw_posts

    def delete_project(self, project_id: int) -> None:
        self.get_project(project_id)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))

    def create_source(
        self,
        project_id: int,
        source_type: str,
        source_config: dict[str, Any],
        is_active: bool = True,
        poll_interval_s: int = 60,
    ) -> dict[str, Any]:
        if source_type not in SUPPORTED_SOURCE_TYPES:
            raise DomainValidationError(
                f"Unsupported source_type '{source_type}'. Use one of: {', '.join(SUPPORTED_SOURCE_TYPES)}."
            )
        normalized_source_config = self._normalize_source_config(
            source_type, source_config
        )

        self._ensure_project_exists(project_id)

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sources (
                    project_id,
                    source_type,
                    source_config,
                    is_active,
                    poll_interval_s
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING
                    id,
                    project_id,
                    source_type,
                    source_config,
                    is_active,
                    poll_interval_s,
                    last_collected_at,
                    last_error,
                    created_at
                """,
                (
                    project_id,
                    source_type,
                    Jsonb(normalized_source_config),
                    is_active,
                    poll_interval_s,
                ),
            )
            row = cur.fetchone()

        return dict(row)

    def list_sources(
        self,
        project_id: int | None = None,
        *,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        conditions: list[str] = []
        params: list[Any] = []

        if project_id is not None:
            conditions.append("s.project_id = %s")
            params.append(project_id)

        if active_only:
            conditions.append("s.is_active = TRUE")

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    s.id,
                    s.project_id,
                    s.source_type,
                    s.source_config,
                    s.is_active,
                    s.poll_interval_s,
                    s.last_collected_at,
                    s.last_error,
                    s.created_at,
                    (
                        SELECT COUNT(*)
                        FROM raw_posts rp
                        WHERE rp.source_id = s.id
                    ) AS raw_posts_count
                FROM sources s
                {where_clause}
                ORDER BY s.project_id, s.id
                """,
                params,
            )
            rows = cur.fetchall()

        return [dict(row) for row in rows]

    def get_source(self, project_id: int, source_id: int) -> dict[str, Any]:
        self._ensure_project_exists(project_id)

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    s.id,
                    s.project_id,
                    s.source_type,
                    s.source_config,
                    s.is_active,
                    s.poll_interval_s,
                    s.last_collected_at,
                    s.last_error,
                    s.created_at,
                    (
                        SELECT COUNT(*)
                        FROM raw_posts rp
                        WHERE rp.source_id = s.id
                    ) AS raw_posts_count
                FROM sources s
                WHERE s.project_id = %s
                  AND s.id = %s
                """,
                (project_id, source_id),
            )
            row = cur.fetchone()

        if row is None:
            raise ResourceNotFoundError(
                f"Source {source_id} was not found in project {project_id}."
            )
        return dict(row)

    def update_source(
        self,
        project_id: int,
        source_id: int,
        *,
        source_type: str | None = None,
        source_config: dict[str, Any] | None = None,
        is_active: bool | None = None,
        poll_interval_s: int | None = None,
    ) -> dict[str, Any]:
        source = self.get_source(project_id, source_id)
        next_source_type = (
            source_type if source_type is not None else source["source_type"]
        )
        if next_source_type not in SUPPORTED_SOURCE_TYPES:
            raise DomainValidationError(
                f"Unsupported source_type '{next_source_type}'. Use one of: {', '.join(SUPPORTED_SOURCE_TYPES)}."
            )
        next_source_config = (
            source_config if source_config is not None else source["source_config"]
        )
        normalized_source_config = self._normalize_source_config(
            next_source_type,
            next_source_config,
        )

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE sources
                SET
                    source_type = %s,
                    source_config = %s,
                    is_active = %s,
                    poll_interval_s = %s
                WHERE id = %s
                  AND project_id = %s
                """,
                (
                    next_source_type,
                    Jsonb(normalized_source_config),
                    is_active if is_active is not None else source["is_active"],
                    poll_interval_s
                    if poll_interval_s is not None
                    else source["poll_interval_s"],
                    source_id,
                    project_id,
                ),
            )

        return self.get_source(project_id, source_id)

    def delete_source(self, project_id: int, source_id: int) -> None:
        self.get_source(project_id, source_id)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM sources WHERE id = %s AND project_id = %s",
                (source_id, project_id),
            )

    def list_due_sources(self, now: datetime | None = None) -> list[dict[str, Any]]:
        current_time = now or datetime.now(UTC)

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    s.id,
                    s.project_id,
                    s.source_type,
                    s.source_config,
                    s.is_active,
                    s.poll_interval_s,
                    s.last_collected_at,
                    s.last_error,
                    s.created_at,
                    p.name AS project_name,
                    p.keywords,
                    p.exclude_keywords,
                    p.risk_words
                FROM sources s
                JOIN projects p ON p.id = s.project_id
                WHERE s.is_active = TRUE
                  AND (
                      s.last_collected_at IS NULL
                      OR s.last_collected_at <= %s - make_interval(secs => s.poll_interval_s)
                  )
                ORDER BY s.last_collected_at NULLS FIRST, s.id
                """,
                (current_time,),
            )
            rows = cur.fetchall()

        return [dict(row) for row in rows]

    def list_active_telegram_channels(self) -> list[str]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT source_config->>'channel' AS channel
                FROM sources
                WHERE is_active = TRUE
                  AND source_type = 'telegram'
                  AND source_config ? 'channel'
                ORDER BY channel
                """
            )
            rows = cur.fetchall()

        return [row["channel"] for row in rows if row["channel"]]

    def save_raw_posts(self, source: dict[str, Any], posts: list[ParsedMessage]) -> int:
        saved_count = 0
        collected_at = datetime.now(UTC)

        with self._connect() as conn, conn.cursor() as cur:
            for post in posts:
                cur.execute(
                    """
                    INSERT INTO raw_posts (
                        source_id,
                        external_id,
                        url,
                        title,
                        text,
                        author,
                        published_at,
                        collected_at,
                        raw_meta
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (source_id, external_id) DO NOTHING
                    RETURNING id
                    """,
                    (
                        source["id"],
                        self._raw_post_external_id(post),
                        post.url,
                        self._raw_post_title(post),
                        post.text or "",
                        self._raw_post_author(post),
                        post.date,
                        collected_at,
                        Jsonb(self._build_raw_post_meta(post)),
                    ),
                )
                inserted = cur.fetchone()
                if inserted is not None:
                    saved_count += 1

            cur.execute(
                """
                UPDATE sources
                SET last_collected_at = NOW(),
                    last_error = NULL
                WHERE id = %s
                """,
                (source["id"],),
            )
            self._insert_event(
                cur,
                project_id=source["project_id"],
                event_type="collector_run",
                payload={"source_id": source["id"], "new_posts_count": saved_count},
            )

        return saved_count

    def record_collection_error(self, source: dict[str, Any], error: str) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE sources
                SET last_error = %s
                WHERE id = %s
                """,
                (error, source["id"]),
            )
            self._insert_event(
                cur,
                project_id=source["project_id"],
                event_type="collector_error",
                payload={
                    "source_id": source["id"],
                    "source_type": source["source_type"],
                    "error": error,
                },
            )

    def fetch_unprocessed_raw_posts(
        self,
        limit: int = 100,
        project_id: int | None = None,
    ) -> list[dict[str, Any]]:
        conditions = [
            "rp.ml_processed = FALSE",
            "rp.ml_failed_at IS NULL",
        ]
        params: list[Any] = []
        if project_id is not None:
            conditions.append("s.project_id = %s")
            params.append(project_id)
        params.append(limit)
        where_clause = " AND ".join(conditions)

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    rp.id,
                    rp.source_id,
                    rp.external_id,
                    rp.url,
                    rp.title,
                    rp.text,
                    rp.author,
                    rp.published_at,
                    rp.collected_at,
                    rp.raw_meta,
                    s.project_id,
                    s.source_type,
                    p.name AS project_name,
                    p.keywords,
                    p.exclude_keywords,
                    p.risk_words
                FROM raw_posts rp
                JOIN sources s ON s.id = rp.source_id
                JOIN projects p ON p.id = s.project_id
                WHERE {where_clause}
                ORDER BY rp.collected_at ASC, rp.id ASC
                LIMIT %s
                """,
                params,
            )
            rows = cur.fetchall()

        return [dict(row) for row in rows]

    def find_similar_mentions(
        self,
        project_id: int,
        embedding: list[float],
        *,
        lookback_days: int = 30,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        embedding_literal = self._vector_literal(embedding)
        cutoff = datetime.now(UTC) - timedelta(days=lookback_days)

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    m.id,
                    m.dedup_group_id,
                    m.is_primary,
                    m.processed_at,
                    (m.embedding <=> CAST(%s AS vector)) AS distance
                FROM mentions m
                WHERE m.project_id = %s
                  AND m.relevance_label = 'relevant'
                  AND m.embedding IS NOT NULL
                  AND m.is_primary = TRUE
                  AND m.processed_at >= %s
                ORDER BY m.embedding <=> CAST(%s AS vector)
                LIMIT %s
                """,
                (
                    embedding_literal,
                    project_id,
                    cutoff,
                    embedding_literal,
                    limit,
                ),
            )
            rows = cur.fetchall()

        return [dict(row) for row in rows]

    def find_similar_clusters(
        self,
        project_id: int,
        embedding: list[float],
        *,
        lookback_days: int = 30,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        embedding_literal = self._vector_literal(embedding)
        cutoff = datetime.now(UTC) - timedelta(days=lookback_days)

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    g.id,
                    g.representative_mention_id,
                    g.mention_count,
                    g.first_seen_at,
                    g.last_seen_at,
                    (g.centroid_embedding <=> CAST(%s AS vector)) AS distance
                FROM dedup_groups g
                WHERE g.project_id = %s
                  AND g.centroid_embedding IS NOT NULL
                  AND COALESCE(g.last_seen_at, g.created_at) >= %s
                ORDER BY g.centroid_embedding <=> CAST(%s AS vector)
                LIMIT %s
                """,
                (
                    embedding_literal,
                    project_id,
                    cutoff,
                    embedding_literal,
                    limit,
                ),
            )
            rows = cur.fetchall()

        return [dict(row) for row in rows]

    def ensure_dedup_group_for_mention(self, project_id: int, mention_id: int) -> int:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    m.dedup_group_id,
                    m.embedding,
                    rp.published_at
                FROM mentions m
                JOIN raw_posts rp ON rp.id = m.raw_post_id
                WHERE m.id = %s AND m.project_id = %s
                """,
                (mention_id, project_id),
            )
            row = cur.fetchone()
            if row is None:
                raise ResourceNotFoundError(f"Mention {mention_id} was not found.")

            existing_group_id = row["dedup_group_id"]
            if existing_group_id is not None:
                return int(existing_group_id)

            embedding_literal = (
                self._vector_literal(row["embedding"])
                if row["embedding"] is not None
                else None
            )
            cur.execute(
                """
                INSERT INTO dedup_groups (
                    project_id,
                    representative_mention_id,
                    mention_count,
                    centroid_embedding,
                    first_seen_at,
                    last_seen_at
                )
                VALUES (%s, %s, 1, CAST(%s AS vector), %s, %s)
                RETURNING id
                """,
                (
                    project_id,
                    mention_id,
                    embedding_literal,
                    row["published_at"],
                    row["published_at"],
                ),
            )
            group_row = cur.fetchone()
            group_id = int(group_row["id"])

            cur.execute(
                """
                UPDATE mentions
                SET dedup_group_id = %s,
                    is_primary = TRUE
                WHERE id = %s
                """,
                (group_id, mention_id),
            )

        return group_id

    def persist_mentions(
        self,
        mention_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not mention_rows:
            return {
                "stored_count": 0,
                "projects": {},
                "sync_rows": [],
            }

        raw_post_ids = [int(item["raw_post_id"]) for item in mention_rows]
        project_stats: dict[int, dict[str, int]] = {}

        with self._connect(autocommit=False) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    rp.id,
                    rp.source_id,
                    rp.author,
                    rp.published_at,
                    rp.collected_at,
                    rp.ml_processed,
                    s.project_id,
                    s.source_type
                FROM raw_posts rp
                JOIN sources s ON s.id = rp.source_id
                WHERE rp.id = ANY(%s)
                """,
                (raw_post_ids,),
            )
            raw_posts = {int(row["id"]): dict(row) for row in cur.fetchall()}

            missing_ids = sorted(set(raw_post_ids) - set(raw_posts))
            if missing_ids:
                raise ResourceNotFoundError(
                    f"raw_posts not found: {', '.join(str(item) for item in missing_ids)}"
                )

            processable_raw_post_ids = {
                raw_post_id
                for raw_post_id, row in raw_posts.items()
                if not row["ml_processed"]
            }
            mention_rows = [
                item
                for item in mention_rows
                if int(item["raw_post_id"]) in processable_raw_post_ids
            ]
            if not mention_rows:
                return {
                    "stored_count": 0,
                    "projects": {},
                    "sync_rows": [],
                }

            sync_rows: list[dict[str, Any]] = []
            touched_groups: set[int] = set()

            for item in mention_rows:
                processed_at = item.get("processed_at") or datetime.now(UTC)
                embedding = item.get("embedding")
                embedding_literal = (
                    self._vector_literal(embedding) if embedding is not None else None
                )
                raw_post = raw_posts[int(item["raw_post_id"])]
                project_id = int(item.get("project_id", raw_post["project_id"]))

                cur.execute(
                    """
                    INSERT INTO mentions (
                        raw_post_id,
                        project_id,
                        relevance_score,
                        relevance_label,
                        sentiment_score,
                        sentiment_label,
                        has_risk_words,
                        embedding,
                        dedup_group_id,
                        is_primary,
                        processed_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s,
                        CAST(%s AS vector),
                        %s, %s, %s
                    )
                    ON CONFLICT (raw_post_id) DO UPDATE SET
                        project_id = EXCLUDED.project_id,
                        relevance_score = EXCLUDED.relevance_score,
                        relevance_label = EXCLUDED.relevance_label,
                        sentiment_score = EXCLUDED.sentiment_score,
                        sentiment_label = EXCLUDED.sentiment_label,
                        has_risk_words = EXCLUDED.has_risk_words,
                        embedding = EXCLUDED.embedding,
                        dedup_group_id = EXCLUDED.dedup_group_id,
                        is_primary = EXCLUDED.is_primary,
                        processed_at = EXCLUDED.processed_at,
                        clickhouse_synced_at = NULL
                    RETURNING
                        id,
                        raw_post_id,
                        project_id,
                        relevance_score,
                        relevance_label,
                        sentiment_score,
                        sentiment_label,
                        has_risk_words,
                        dedup_group_id,
                        is_primary,
                        processed_at
                    """,
                    (
                        item["raw_post_id"],
                        project_id,
                        item["relevance_score"],
                        item["relevance_label"],
                        item["sentiment_score"],
                        item["sentiment_label"],
                        item["has_risk_words"],
                        embedding_literal,
                        item.get("dedup_group_id"),
                        item["is_primary"],
                        processed_at,
                    ),
                )
                mention = dict(cur.fetchone())

                group_id = mention["dedup_group_id"]
                if group_id is not None:
                    touched_groups.add(int(group_id))

                project_id = int(mention["project_id"])
                stats = project_stats.setdefault(
                    project_id,
                    {
                        "batch_size": 0,
                        "relevant_count": 0,
                        "irrelevant_count": 0,
                        "dedup_count": 0,
                    },
                )
                stats["batch_size"] += 1
                if mention["relevance_label"] == "relevant":
                    stats["relevant_count"] += 1
                else:
                    stats["irrelevant_count"] += 1
                if group_id is not None or not mention["is_primary"]:
                    stats["dedup_count"] += 1

                sync_rows.append(
                    {
                        "mention_id": int(mention["id"]),
                        "project_id": project_id,
                        "source_type": raw_post["source_type"],
                        "source_id": int(raw_post["source_id"]),
                        "author": raw_post["author"] or "",
                        "relevance_score": float(mention["relevance_score"]),
                        "relevance_label": mention["relevance_label"],
                        "sentiment_score": float(mention["sentiment_score"]),
                        "sentiment_label": mention["sentiment_label"],
                        "has_risk_words": int(bool(mention["has_risk_words"])),
                        "is_primary": int(bool(mention["is_primary"])),
                        "published_at": raw_post["published_at"],
                        "collected_at": raw_post["collected_at"],
                        "processed_at": mention["processed_at"],
                        "dedup_group_id": int(group_id or 0),
                    }
                )

            for group_id in touched_groups:
                self._refresh_dedup_group(cur, group_id)

            persisted_raw_post_ids = [int(item["raw_post_id"]) for item in mention_rows]

            cur.execute(
                """
                UPDATE raw_posts
                SET ml_processed = TRUE,
                    ml_failed_at = NULL,
                    ml_error = NULL
                WHERE id = ANY(%s)
                """,
                (persisted_raw_post_ids,),
            )

            for project_id, stats in project_stats.items():
                self._insert_event(
                    cur,
                    project_id=project_id,
                    event_type="ml_processed",
                    payload=stats,
                )

            conn.commit()

        return {
            "stored_count": len(mention_rows),
            "projects": project_stats,
            "sync_rows": sync_rows,
        }

    def list_clusters(
        self,
        project_id: int,
        *,
        page: int = 1,
        page_size: int = 100,
        confidence_threshold: float | None = None,
        published_after: datetime | None = None,
        sentiment_label: str | None = None,
        risk_words_only: bool = False,
    ) -> dict[str, Any]:
        conditions = [
            "m.project_id = %s",
            "m.relevance_label = 'relevant'",
        ]
        params: list[Any] = [project_id]

        if confidence_threshold is not None:
            conditions.append("m.relevance_score >= %s")
            params.append(confidence_threshold)

        if published_after is not None:
            conditions.append("rp.published_at >= %s")
            params.append(published_after)

        if sentiment_label is not None:
            conditions.append("m.sentiment_label = %s")
            params.append(sentiment_label)

        if risk_words_only:
            conditions.append("m.has_risk_words = TRUE")

        where_clause = " AND ".join(conditions)
        offset = (page - 1) * page_size
        base_cte = f"""
            WITH filtered_mentions AS (
                SELECT
                    m.id,
                    m.raw_post_id,
                    m.project_id,
                    m.relevance_score,
                    m.relevance_label,
                    m.sentiment_score,
                    m.sentiment_label,
                    m.has_risk_words,
                    m.dedup_group_id,
                    m.is_primary,
                    m.processed_at,
                    rp.source_id,
                    s.source_type,
                    rp.external_id,
                    rp.url,
                    rp.title,
                    rp.text,
                    rp.author,
                    rp.published_at,
                    rp.collected_at,
                    COALESCE(m.dedup_group_id, -m.id) AS cluster_id
                FROM mentions m
                JOIN raw_posts rp ON rp.id = m.raw_post_id
                JOIN sources s ON s.id = rp.source_id
                WHERE {where_clause}
            ),
            ranked_clusters AS (
                SELECT
                    fm.*,
                    COUNT(*) OVER (PARTITION BY fm.cluster_id) AS mentions_count,
                    MIN(fm.published_at) OVER (PARTITION BY fm.cluster_id) AS first_seen_at,
                    MAX(fm.published_at) OVER (PARTITION BY fm.cluster_id) AS last_seen_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY fm.cluster_id
                        ORDER BY
                            CASE WHEN fm.is_primary THEN 0 ELSE 1 END,
                            fm.processed_at DESC,
                            fm.id DESC
                    ) AS cluster_rank
                FROM filtered_mentions fm
            )
        """

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                base_cte
                + """
                SELECT COUNT(*) AS total
                FROM (
                    SELECT DISTINCT cluster_id
                    FROM filtered_mentions
                ) clusters
                """,
                params,
            )
            total_row = cur.fetchone()

            cur.execute(
                base_cte
                + """
                SELECT
                    rc.cluster_id,
                    rc.dedup_group_id,
                    rc.mentions_count,
                    rc.first_seen_at,
                    rc.last_seen_at,
                    rc.id AS representative_mention_id,
                    rc.raw_post_id,
                    rc.project_id,
                    rc.relevance_score,
                    rc.relevance_label,
                    rc.sentiment_score,
                    rc.sentiment_label,
                    rc.has_risk_words,
                    rc.processed_at,
                    rc.source_id,
                    rc.source_type,
                    rc.external_id,
                    rc.url,
                    rc.title,
                    rc.text,
                    rc.author,
                    rc.published_at,
                    rc.collected_at
                FROM ranked_clusters rc
                WHERE rc.cluster_rank = 1
                ORDER BY rc.last_seen_at DESC, rc.id DESC
                LIMIT %s
                OFFSET %s
                """,
                [*params, page_size, offset],
            )
            rows = cur.fetchall()

        return {
            "items": [dict(row) for row in rows],
            "total": int(total_row["total"]) if total_row is not None else 0,
        }

    def mark_raw_posts_ml_failed(self, failures: list[dict[str, Any]]) -> int:
        if not failures:
            return 0

        with self._connect() as conn, conn.cursor() as cur:
            for failure in failures:
                cur.execute(
                    """
                    UPDATE raw_posts
                    SET ml_failed_at = NOW(),
                        ml_error = %s
                    WHERE id = %s
                      AND ml_processed = FALSE
                    """,
                    (failure["error"], int(failure["raw_post_id"])),
                )

        return len(failures)

    def fetch_pending_mention_events(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    m.id AS mention_id,
                    m.project_id,
                    s.source_type,
                    rp.source_id,
                    COALESCE(rp.author, '') AS author,
                    m.relevance_score,
                    m.relevance_label,
                    m.sentiment_score,
                    m.sentiment_label,
                    CASE WHEN m.has_risk_words THEN 1 ELSE 0 END AS has_risk_words,
                    CASE WHEN m.is_primary THEN 1 ELSE 0 END AS is_primary,
                    rp.published_at,
                    rp.collected_at,
                    m.processed_at,
                    COALESCE(m.dedup_group_id, 0) AS dedup_group_id
                FROM mentions m
                JOIN raw_posts rp ON rp.id = m.raw_post_id
                JOIN sources s ON s.id = rp.source_id
                WHERE m.clickhouse_synced_at IS NULL
                ORDER BY m.processed_at ASC, m.id ASC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

        return [dict(row) for row in rows]

    def mark_mentions_clickhouse_synced(self, mention_ids: list[int]) -> int:
        if not mention_ids:
            return 0

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE mentions
                SET clickhouse_synced_at = NOW()
                WHERE id = ANY(%s)
                """,
                (mention_ids,),
            )
            updated = cur.rowcount

        return int(updated or 0)

    def list_raw_posts(self, project_id: int, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    rp.id,
                    rp.source_id,
                    s.source_type,
                    rp.external_id,
                    rp.url,
                    rp.title,
                    rp.text,
                    rp.author,
                    rp.published_at,
                    rp.collected_at,
                    rp.raw_meta,
                    rp.ml_processed
                FROM raw_posts rp
                JOIN sources s ON s.id = rp.source_id
                WHERE s.project_id = %s
                ORDER BY rp.published_at DESC, rp.id DESC
                LIMIT %s
                """,
                (project_id, limit),
            )
            rows = cur.fetchall()

        return [dict(row) for row in rows]

    def get_raw_post_processing_stats(
        self, project_id: int | None = None
    ) -> dict[str, int]:
        params: list[Any] = []
        where_clause = ""
        if project_id is not None:
            where_clause = "WHERE s.project_id = %s"
            params.append(project_id)

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE rp.ml_processed = TRUE) AS processed,
                    COUNT(*) FILTER (
                        WHERE rp.ml_processed = FALSE
                          AND rp.ml_failed_at IS NULL
                    ) AS pending,
                    COUNT(*) FILTER (
                        WHERE rp.ml_processed = FALSE
                          AND rp.ml_failed_at IS NOT NULL
                    ) AS failed
                FROM raw_posts rp
                JOIN sources s ON s.id = rp.source_id
                {where_clause}
                """,
                params,
            )
            row = cur.fetchone()

        if row is None:
            return {
                "total": 0,
                "processed": 0,
                "pending": 0,
                "failed": 0,
            }

        return {
            "total": int(row["total"] or 0),
            "processed": int(row["processed"] or 0),
            "pending": int(row["pending"] or 0),
            "failed": int(row["failed"] or 0),
        }

    def list_mentions(
        self,
        project_id: int,
        *,
        page: int = 1,
        page_size: int = 100,
        confidence_threshold: float | None = None,
        published_after: datetime | None = None,
        sentiment_label: str | None = None,
        dedup_group_id: int | None = None,
        primary_only: bool = False,
        relevant_only: bool = False,
        include_total: bool = True,
        risk_words_only: bool = False,
    ) -> dict[str, Any]:
        conditions = ["m.project_id = %s"]
        params: list[Any] = [project_id]

        if primary_only:
            conditions.append("m.is_primary = TRUE")

        if relevant_only:
            conditions.append("m.relevance_label = 'relevant'")

        if confidence_threshold is not None:
            conditions.append("m.relevance_score >= %s")
            params.append(confidence_threshold)

        if published_after is not None:
            conditions.append("rp.published_at >= %s")
            params.append(published_after)

        if sentiment_label is not None:
            conditions.append("m.sentiment_label = %s")
            params.append(sentiment_label)

        if dedup_group_id is not None:
            conditions.append("m.dedup_group_id = %s")
            params.append(dedup_group_id)

        if risk_words_only:
            conditions.append("m.has_risk_words = TRUE")

        where_clause = " AND ".join(conditions)
        offset = (page - 1) * page_size

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    m.id,
                    m.raw_post_id,
                    m.project_id,
                    m.relevance_score,
                    m.relevance_label,
                    m.sentiment_score,
                    m.sentiment_label,
                    m.has_risk_words,
                    m.dedup_group_id,
                    m.is_primary,
                    m.resolved,
                    m.processed_at,
                    rp.source_id,
                    s.source_type,
                    rp.external_id,
                    rp.url,
                    rp.title,
                    rp.text,
                    rp.author,
                    rp.published_at,
                    rp.collected_at
                FROM mentions m
                JOIN raw_posts rp ON rp.id = m.raw_post_id
                JOIN sources s ON s.id = rp.source_id
                WHERE {where_clause}
                ORDER BY rp.published_at DESC, rp.id DESC
                LIMIT %s
                OFFSET %s
                """,
                [*params, page_size, offset],
            )
            rows = cur.fetchall()

            total: int | None = None
            if include_total:
                cur.execute(
                    f"""
                    SELECT COUNT(*) AS total
                    FROM mentions m
                    JOIN raw_posts rp ON rp.id = m.raw_post_id
                    JOIN sources s ON s.id = rp.source_id
                    WHERE {where_clause}
                    """,
                    params,
                )
                total_row = cur.fetchone()
                total = int(total_row["total"]) if total_row is not None else 0

        return {
            "items": [dict(row) for row in rows],
            "total": total,
        }

    def update_mention_resolved(
        self,
        project_id: int,
        mention_id: int,
        *,
        resolved: bool,
    ) -> dict[str, Any]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE mentions
                SET resolved = %s
                WHERE id = %s
                  AND project_id = %s
                RETURNING id
                """,
                (resolved, mention_id, project_id),
            )
            row = cur.fetchone()

            if row is None:
                raise ResourceNotFoundError(
                    f"Mention {mention_id} was not found in project {project_id}."
                )

            cur.execute(
                """
                SELECT
                    m.id,
                    m.raw_post_id,
                    m.project_id,
                    m.relevance_score,
                    m.relevance_label,
                    m.sentiment_score,
                    m.sentiment_label,
                    m.has_risk_words,
                    m.dedup_group_id,
                    m.is_primary,
                    m.resolved,
                    m.processed_at,
                    rp.source_id,
                    s.source_type,
                    rp.external_id,
                    rp.url,
                    rp.title,
                    rp.text,
                    rp.author,
                    rp.published_at,
                    rp.collected_at
                FROM mentions m
                JOIN raw_posts rp ON rp.id = m.raw_post_id
                JOIN sources s ON s.id = rp.source_id
                WHERE m.project_id = %s
                  AND m.id = %s
                """,
                (project_id, mention_id),
            )
            mention_row = cur.fetchone()

        if mention_row is None:
            raise ResourceNotFoundError(
                f"Mention {mention_id} was not found in project {project_id}."
            )
        return dict(mention_row)

    def count_unprocessed_raw_posts(self, project_id: int | None = None) -> int:
        conditions = [
            "rp.ml_processed = FALSE",
            "rp.ml_failed_at IS NULL",
        ]
        params: list[Any] = []
        if project_id is not None:
            conditions.append("s.project_id = %s")
            params.append(project_id)
        where_clause = " AND ".join(conditions)

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM raw_posts rp
                JOIN sources s ON s.id = rp.source_id
                WHERE {where_clause}
                """,
                params,
            )
            row = cur.fetchone()

        return int(row["total"])

    @staticmethod
    def _normalize_source_config(
        source_type: str,
        source_config: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(source_config, dict):
            raise DomainValidationError("source_config must be a JSON object.")

        normalized_source_config = dict(source_config)
        url = normalized_source_config.get("url")
        if source_type in {"rss", "website"}:
            if not isinstance(url, str) or not url.strip():
                raise DomainValidationError(
                    f"{source_type.upper()} source_config.url is required."
                )

            normalized_url = url.strip()
            if source_type == "rss" and normalized_url == LEGACY_BOOTSTRAP_RSS_URL:
                normalized_url = DEFAULT_BOOTSTRAP_SOURCES[2]["source_config"]["url"]
            parsed = urlparse(normalized_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise DomainValidationError(
                    f"{source_type.upper()} source_config.url must be a valid http(s) URL."
                )

            normalized_source_config["url"] = normalized_url

        if source_type != "website":
            return normalized_source_config

        for key in WEBSITE_SELECTOR_KEYS:
            if key not in normalized_source_config:
                continue
            value = normalized_source_config[key]
            if not isinstance(value, str) or not value.strip():
                raise DomainValidationError(
                    f"Website source_config.{key} must be a non-empty string."
                )
            normalized_source_config[key] = value.strip()

        return normalized_source_config

    @staticmethod
    def _raw_post_external_id(post: ParsedMessage) -> str:
        external_id = post.meta.get("external_id") if post.meta else None
        if isinstance(external_id, str) and external_id.strip():
            return external_id.strip()
        return str(post.id)

    @staticmethod
    def _raw_post_title(post: ParsedMessage) -> str | None:
        if isinstance(post.title, str):
            title = post.title.strip()
            if title:
                return title
        return None

    @staticmethod
    def _raw_post_author(post: ParsedMessage) -> str | None:
        return post.post_author or post.source.username or post.source.title

    @staticmethod
    def _build_raw_post_meta(post: ParsedMessage) -> dict[str, Any]:
        payload = {
            "message_uid": post.message_uid,
            "channel_id": post.source.channel_id,
            "channel_title": post.source.title,
            "channel_username": post.source.username,
            "requested_as": post.source.requested_as,
            "views": post.views,
            "forwards": post.forwards,
            "like_count": post.like_count,
            "dislike_count": post.dislike_count,
            "reactions": [reaction.model_dump() for reaction in post.reactions],
        }
        if post.title:
            payload["title"] = post.title
        if post.meta:
            payload.update(post.meta)
        return payload

    def _insert_event(
        self,
        cur: psycopg.Cursor,
        *,
        project_id: int | None,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        cur.execute(
            """
            INSERT INTO events (
                project_id,
                event_type,
                payload
            )
            VALUES (%s, %s, %s)
            """,
            (
                project_id,
                event_type,
                Jsonb(payload),
            ),
        )

    @staticmethod
    def _vector_literal(embedding: list[float] | tuple[float, ...] | str) -> str:
        values: list[float]
        if isinstance(embedding, str):
            normalized = embedding.strip()
            if normalized.startswith("[") and normalized.endswith("]"):
                inner = normalized[1:-1].strip()
                parts = [] if not inner else [part.strip() for part in inner.split(",")]
                values = [float(part) for part in parts]
            else:
                raise ValueError("Embedding string must use pgvector literal format.")
        else:
            values = [float(value) for value in embedding]
        return "[" + ",".join(f"{value:.10f}" for value in values) + "]"

    def _refresh_dedup_group(self, cur: psycopg.Cursor, group_id: int) -> None:
        cur.execute(
            """
            UPDATE dedup_groups
            SET
                mention_count = (
                    SELECT COUNT(*)
                    FROM mentions
                    WHERE dedup_group_id = %s
                ),
                representative_mention_id = COALESCE(
                    (
                        SELECT id
                        FROM mentions
                        WHERE dedup_group_id = %s
                          AND is_primary = TRUE
                        ORDER BY processed_at ASC, id ASC
                        LIMIT 1
                    ),
                    (
                        SELECT id
                        FROM mentions
                        WHERE dedup_group_id = %s
                        ORDER BY processed_at ASC, id ASC
                        LIMIT 1
                    )
                ),
                first_seen_at = (
                    SELECT MIN(rp.published_at)
                    FROM mentions m
                    JOIN raw_posts rp ON rp.id = m.raw_post_id
                    WHERE m.dedup_group_id = %s
                ),
                last_seen_at = (
                    SELECT MAX(rp.published_at)
                    FROM mentions m
                    JOIN raw_posts rp ON rp.id = m.raw_post_id
                    WHERE m.dedup_group_id = %s
                ),
                centroid_embedding = (
                    SELECT AVG(embedding)
                    FROM mentions
                    WHERE dedup_group_id = %s
                      AND embedding IS NOT NULL
                )
            WHERE id = %s
            """,
            (group_id, group_id, group_id, group_id, group_id, group_id, group_id),
        )

    @staticmethod
    def _source_config_key(source_config: dict[str, Any]) -> str:
        return json.dumps(source_config, sort_keys=True, ensure_ascii=True)

    def _ensure_project_exists(self, project_id: int) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT id FROM projects WHERE id = %s", (project_id,))
            row = cur.fetchone()

        if row is None:
            raise ResourceNotFoundError(f"Project {project_id} was not found.")

    def _connect(self, *, autocommit: bool = True):
        return psycopg.connect(
            self.settings.parser_database_url,
            autocommit=autocommit,
            row_factory=dict_row,
        )
