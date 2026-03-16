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

CREATE INDEX IF NOT EXISTS idx_raw_posts_unprocessed
ON raw_posts (ml_processed)
WHERE NOT ml_processed;

CREATE INDEX IF NOT EXISTS idx_raw_posts_ml_queue
ON raw_posts (collected_at ASC, id ASC)
WHERE ml_processed = FALSE AND ml_failed_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_raw_posts_source_published
ON raw_posts (source_id, published_at DESC);
