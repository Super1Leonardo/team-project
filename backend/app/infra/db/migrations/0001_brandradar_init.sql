CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    keywords TEXT[] NOT NULL,
    exclude_keywords TEXT[] NOT NULL DEFAULT '{}',
    risk_words TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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
);

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
);

CREATE TABLE IF NOT EXISTS dedup_groups (
    id BIGSERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    representative_mention_id BIGINT,
    mention_count INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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

CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    project_id INT,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_posts_unprocessed
ON raw_posts (ml_processed)
WHERE NOT ml_processed;

CREATE INDEX IF NOT EXISTS idx_raw_posts_ml_queue
ON raw_posts (collected_at ASC, id ASC)
WHERE ml_processed = FALSE AND ml_failed_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_raw_posts_source_published
ON raw_posts (source_id, published_at DESC);

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

CREATE INDEX IF NOT EXISTS idx_events_lookup
ON events (project_id, created_at DESC);
