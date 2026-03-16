from __future__ import annotations

import unittest

from backend.app.core.config import Settings
from backend.app.infra.db.postgres import BrandRadarPostgresStore


class _FakeCursor:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state
        self._row: dict[str, object] | None = None

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params=None) -> None:
        normalized_query = " ".join(query.split())

        if normalized_query == "SELECT id FROM projects ORDER BY id ASC LIMIT 1":
            project = self.state["project"]
            self._row = None if project is None else {"id": project["id"]}
            return

        if normalized_query.startswith("INSERT INTO projects"):
            project = {
                "id": 1,
                "name": params[0],
                "keywords": params[1],
                "exclude_keywords": params[2],
                "risk_words": params[3],
            }
            self.state["project"] = project
            self._row = {"id": 1}
            return

        if normalized_query.startswith("INSERT INTO sources"):
            source_config = getattr(params[2], "obj", params[2])
            self.state["sources"].append(
                {
                    "project_id": params[0],
                    "source_type": params[1],
                    "source_config": source_config,
                    "is_active": params[3],
                    "poll_interval_s": params[4],
                }
            )
            self._row = None
            return

        raise AssertionError(f"Unexpected query: {normalized_query}")

    def fetchone(self) -> dict[str, object] | None:
        return self._row


class _FakeConnection:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self.state)

    def commit(self) -> None:
        self.state["commits"] += 1


class PostgresBootstrapTests(unittest.TestCase):
    def _build_store(self, state: dict[str, object]) -> BrandRadarPostgresStore:
        store = BrandRadarPostgresStore(Settings())
        store._connect = lambda autocommit=True: _FakeConnection(state)  # type: ignore[method-assign]
        return store

    def test_bootstrap_default_project_and_sources_seeds_empty_db(self) -> None:
        state = {
            "project": None,
            "sources": [],
            "commits": 0,
        }
        store = self._build_store(state)

        store.bootstrap_default_project_and_sources()

        self.assertEqual(
            state["project"],
            {
                "id": 1,
                "name": "Brand Radar",
                "keywords": [],
                "exclude_keywords": [],
                "risk_words": [],
            },
        )
        self.assertEqual(
            state["sources"],
            [
                {
                    "project_id": 1,
                    "source_type": "telegram",
                    "source_config": {"channel": "https://t.me/brand_radar_case"},
                    "is_active": True,
                    "poll_interval_s": 300,
                },
                {
                    "project_id": 1,
                    "source_type": "website",
                    "source_config": {"url": "http://web-brandradar.ingress.prodcontest.com/"},
                    "is_active": True,
                    "poll_interval_s": 300,
                },
                {
                    "project_id": 1,
                    "source_type": "rss",
                    "source_config": {"url": "http://rss-brandradar.ingress.prodcontest.com/"},
                    "is_active": True,
                    "poll_interval_s": 300,
                },
            ],
        )
        self.assertEqual(state["commits"], 1)

    def test_bootstrap_default_project_and_sources_skips_non_empty_db(self) -> None:
        state = {
            "project": {"id": 99},
            "sources": [],
            "commits": 0,
        }
        store = self._build_store(state)

        store.bootstrap_default_project_and_sources()

        self.assertEqual(state["project"], {"id": 99})
        self.assertEqual(state["sources"], [])
        self.assertEqual(state["commits"], 0)
