# BrandRadar migrations

This directory now contains two schema handoff formats for the MVP:

- `0001_brandradar_init.sql`: one-shot baseline snapshot for bootstrapping a clean database
- `0010_extensions.sql` ... `0016_events.sql`: the same schema split into per-table SQL files

Use the split files when you need to:
- review one table at a time
- discuss ownership of schema parts in the backend team
- prepare for a later move to Alembic or Flyway

Apply the split files in this order:
1. `0010_extensions.sql`
2. `0011_projects.sql`
3. `0012_sources.sql`
4. `0013_raw_posts.sql`
5. `0014_dedup_groups.sql`
6. `0015_mentions.sql`
7. `0016_events.sql`

Runtime startup still calls `init_db()` for backward-compatible local bootstrap. These SQL files are still baselines, not a full migration history.
