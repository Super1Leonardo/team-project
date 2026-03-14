from __future__ import annotations

import time

import psycopg
from psycopg.types.json import Jsonb

from backend.app.common.schemas import MLOffsetUpdate, MLResultInput
from backend.app.core.config import Settings


class MLResultsRepository:
    def __init__(self, settings: Settings):
        self.settings = settings

    def init_db(self, retries: int = 10, delay_seconds: float = 1.0) -> None:
        last_error: Exception | None = None

        for attempt in range(retries):
            try:
                with self._connect() as conn, conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS mention_ml_results (
                            id BIGSERIAL PRIMARY KEY,
                            message_uid TEXT NOT NULL UNIQUE,
                            project_id TEXT NOT NULL DEFAULT 'default',
                            relevance_label BOOLEAN,
                            relevance_score DOUBLE PRECISION,
                            sentiment_label TEXT,
                            sentiment_score DOUBLE PRECISION,
                            aggression_score DOUBLE PRECISION,
                            womp_score DOUBLE PRECISION,
                            dedup_group_id TEXT,
                            is_canonical BOOLEAN NOT NULL DEFAULT TRUE,
                            story_cluster_id TEXT,
                            model_version TEXT,
                            features_json JSONB,
                            processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS ml_offsets (
                            consumer_name TEXT PRIMARY KEY,
                            last_collected_at TIMESTAMPTZ,
                            last_message_uid TEXT,
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_mention_ml_results_project_id
                        ON mention_ml_results(project_id)
                        """
                    )
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_mention_ml_results_sentiment
                        ON mention_ml_results(sentiment_label)
                        """
                    )
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_mention_ml_results_relevance
                        ON mention_ml_results(relevance_label, relevance_score DESC)
                        """
                    )
                    cur.execute(
                        """
                        CREATE INDEX IF NOT EXISTS idx_mention_ml_results_processed_at
                        ON mention_ml_results(processed_at DESC)
                        """
                    )
                return
            except psycopg.OperationalError as exc:
                last_error = exc
                if attempt == retries - 1:
                    break
                time.sleep(delay_seconds)

        if last_error is not None:
            raise last_error

    def save_results(self, results: list[MLResultInput]) -> int:
        rows = [
            (
                result.message_uid,
                result.project_id,
                result.relevance_label,
                result.relevance_score,
                result.sentiment_label,
                result.sentiment_score,
                result.aggression_score,
                result.womp_score,
                result.dedup_group_id,
                result.is_canonical,
                result.story_cluster_id,
                result.model_version,
                Jsonb(result.features) if result.features is not None else None,
                result.processed_at,
            )
            for result in results
        ]

        if not rows:
            return 0

        with self._connect() as conn, conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO mention_ml_results (
                    message_uid,
                    project_id,
                    relevance_label,
                    relevance_score,
                    sentiment_label,
                    sentiment_score,
                    aggression_score,
                    womp_score,
                    dedup_group_id,
                    is_canonical,
                    story_cluster_id,
                    model_version,
                    features_json,
                    processed_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, COALESCE(%s, NOW())
                )
                ON CONFLICT (message_uid) DO UPDATE SET
                    project_id = EXCLUDED.project_id,
                    relevance_label = COALESCE(
                        EXCLUDED.relevance_label,
                        mention_ml_results.relevance_label
                    ),
                    relevance_score = COALESCE(
                        EXCLUDED.relevance_score,
                        mention_ml_results.relevance_score
                    ),
                    sentiment_label = COALESCE(
                        EXCLUDED.sentiment_label,
                        mention_ml_results.sentiment_label
                    ),
                    sentiment_score = COALESCE(
                        EXCLUDED.sentiment_score,
                        mention_ml_results.sentiment_score
                    ),
                    aggression_score = COALESCE(
                        EXCLUDED.aggression_score,
                        mention_ml_results.aggression_score
                    ),
                    womp_score = COALESCE(
                        EXCLUDED.womp_score,
                        mention_ml_results.womp_score
                    ),
                    dedup_group_id = COALESCE(
                        EXCLUDED.dedup_group_id,
                        mention_ml_results.dedup_group_id
                    ),
                    is_canonical = EXCLUDED.is_canonical,
                    story_cluster_id = COALESCE(
                        EXCLUDED.story_cluster_id,
                        mention_ml_results.story_cluster_id
                    ),
                    model_version = COALESCE(
                        EXCLUDED.model_version,
                        mention_ml_results.model_version
                    ),
                    features_json = COALESCE(
                        EXCLUDED.features_json,
                        mention_ml_results.features_json
                    ),
                    processed_at = COALESCE(
                        EXCLUDED.processed_at,
                        mention_ml_results.processed_at,
                        NOW()
                    )
                """,
                rows,
            )

        return len(rows)

    def update_offset(self, offset: MLOffsetUpdate) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ml_offsets (
                    consumer_name,
                    last_collected_at,
                    last_message_uid
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (consumer_name) DO UPDATE SET
                    last_collected_at = COALESCE(
                        EXCLUDED.last_collected_at,
                        ml_offsets.last_collected_at
                    ),
                    last_message_uid = COALESCE(
                        EXCLUDED.last_message_uid,
                        ml_offsets.last_message_uid
                    ),
                    updated_at = NOW()
                """,
                (
                    offset.consumer_name,
                    offset.last_collected_at,
                    offset.last_message_uid,
                ),
            )

    def _connect(self):
        return psycopg.connect(self.settings.parser_database_url, autocommit=True)
