# BrandRadar migrations

`0001_brandradar_init.sql` is the canonical SQL snapshot for the MVP schema.

Use it for:
- bootstrapping a clean Postgres instance for a second backend team
- reviewing the public data model without reading `init_db()` in Python
- creating a first Alembic or Flyway baseline later

Runtime startup still calls `init_db()` for backward-compatible local bootstrap, but the SQL file is the safer handoff artifact.
