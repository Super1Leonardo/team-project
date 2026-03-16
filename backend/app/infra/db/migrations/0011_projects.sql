CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    keywords TEXT[] NOT NULL,
    exclude_keywords TEXT[] NOT NULL DEFAULT '{}',
    risk_words TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
