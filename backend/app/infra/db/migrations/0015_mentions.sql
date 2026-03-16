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
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    clickhouse_synced_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_mentions_embedding
ON mentions
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_mentions_feed
ON mentions (project_id, processed_at DESC)
WHERE relevance_label = 'relevant' AND is_primary = TRUE;

CREATE INDEX IF NOT EXISTS idx_mentions_clickhouse_pending
ON mentions (processed_at ASC, id ASC)
WHERE clickhouse_synced_at IS NULL;
