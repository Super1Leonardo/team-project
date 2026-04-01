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
