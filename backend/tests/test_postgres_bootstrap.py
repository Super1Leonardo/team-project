from __future__ import annotations

import copy
import unittest
from datetime import UTC, datetime
from typing import Any

from backend.app.core.config import Settings
from backend.app.infra.db.postgres import (
    DEFAULT_BOOTSTRAP_PROJECT,
    DEFAULT_BOOTSTRAP_SOURCES,
    BrandRadarPostgresStore,
)


class _FakeCursor:
    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state
        self._row: dict[str, Any] | None = None
        self._rows: list[dict[str, Any]] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def execute(self, query: str, params=None) -> None:
        normalized_query = " ".join(query.split())
        self._row = None
        self._rows = []

        if normalized_query == (
            "SELECT id FROM projects WHERE name = %s ORDER BY id ASC LIMIT 1"
        ):
            project_name = params[0]
            project = next(
                (
                    item
                    for item in sorted(self.state["projects"], key=lambda row: row["id"])
                    if item["name"] == project_name
                ),
                None,
            )
            self._row = None if project is None else {"id": project["id"]}
            return

        if normalized_query.startswith("INSERT INTO projects"):
            new_id = self._next_project_id()
            project = {
                "id": new_id,
                "name": params[0],
                "keywords": list(params[1]),
                "exclude_keywords": list(params[2]),
                "risk_words": list(params[3]),
                "created_at": datetime(2026, 3, 16, 12, 0, tzinfo=UTC),
            }
            self.state["projects"].append(project)
            self._row = {"id": new_id}
            return

        if normalized_query == (
            "SELECT id, source_type, source_config FROM sources "
            "WHERE project_id = %s ORDER BY id ASC"
        ):
            project_id = int(params[0])
            self._rows = [
                {
                    "id": source["id"],
                    "source_type": source["source_type"],
                    "source_config": copy.deepcopy(source["source_config"]),
                }
                for source in sorted(self.state["sources"], key=lambda row: row["id"])
                if int(source["project_id"]) == project_id
            ]
            return

        if normalized_query.startswith("INSERT INTO sources"):
            new_id = self._next_source_id()
            source_config = copy.deepcopy(getattr(params[2], "obj", params[2]))
            self.state["sources"].append(
                {
                    "id": new_id,
                    "project_id": int(params[0]),
                    "source_type": params[1],
                    "source_config": source_config,
                    "is_active": params[3],
                    "poll_interval_s": params[4],
                }
            )
            return

        if normalized_query.startswith(
            "SELECT p.id, p.name, p.keywords, p.exclude_keywords,"
        ):
            default_project_name = params[0]
            self._rows = [
                {
                    "id": project["id"],
                    "name": project["name"],
                    "keywords": copy.deepcopy(project["keywords"]),
                    "exclude_keywords": copy.deepcopy(project["exclude_keywords"]),
                    "risk_words": copy.deepcopy(project["risk_words"]),
                    "created_at": project["created_at"],
                    "sources_count": sum(
                        1
                        for source in self.state["sources"]
                        if int(source["project_id"]) == int(project["id"])
                    ),
                    "mentions_count": int(
                        self.state["mentions_count"].get(int(project["id"]), 0)
                    ),
                }
                for project in sorted(
                    self.state["projects"],
                    key=lambda row: (
                        0 if row["name"] == default_project_name else 1,
                        -row["created_at"].timestamp(),
                        -int(row["id"]),
                    ),
                )
            ]
            return

        raise AssertionError(f"Unexpected query: {normalized_query}")

    def fetchone(self) -> dict[str, Any] | None:
        return self._row

    def fetchall(self) -> list[dict[str, Any]]:
        return self._rows

    def _next_project_id(self) -> int:
        existing_ids = [int(project["id"]) for project in self.state["projects"]]
        return max(existing_ids, default=0) + 1

    def _next_source_id(self) -> int:
        existing_ids = [int(source["id"]) for source in self.state["sources"]]
        return max(existing_ids, default=0) + 1


class _FakeConnection:
    def __init__(self, state: dict[str, Any]) -> None:
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
    def _build_store(self, state: dict[str, Any]) -> BrandRadarPostgresStore:
        store = BrandRadarPostgresStore(Settings())
        store._connect = lambda autocommit=True: _FakeConnection(state)  # type: ignore[method-assign]
        return store

    def _default_sources_for_project(self, project_id: int) -> list[dict[str, Any]]:
        return [
            {
                "id": index,
                "project_id": project_id,
                "source_type": source["source_type"],
                "source_config": copy.deepcopy(source["source_config"]),
                "is_active": source["is_active"],
                "poll_interval_s": source["poll_interval_s"],
            }
            for index, source in enumerate(DEFAULT_BOOTSTRAP_SOURCES, start=1)
        ]

    def test_bootstrap_default_project_and_sources_seeds_empty_db(self) -> None:
        state = {
            "projects": [],
            "sources": [],
            "mentions_count": {},
            "commits": 0,
        }
        store = self._build_store(state)

        store.bootstrap_default_project_and_sources()

        self.assertEqual(
            state["projects"],
            [
                {
                    "id": 1,
                    "name": DEFAULT_BOOTSTRAP_PROJECT["name"],
                    "keywords": [],
                    "exclude_keywords": [],
                    "risk_words": [],
                    "created_at": datetime(2026, 3, 16, 12, 0, tzinfo=UTC),
                }
            ],
        )
        self.assertEqual(state["sources"], self._default_sources_for_project(1))
        self.assertEqual(state["commits"], 1)

    def test_bootstrap_default_project_and_sources_adds_default_project_on_live_db(self) -> None:
        state = {
            "projects": [
                {
                    "id": 7,
                    "name": "User Project",
                    "keywords": ["bank"],
                    "exclude_keywords": [],
                    "risk_words": [],
                    "created_at": datetime(2026, 3, 15, 12, 0, tzinfo=UTC),
                }
            ],
            "sources": [],
            "mentions_count": {},
            "commits": 0,
        }
        store = self._build_store(state)

        store.bootstrap_default_project_and_sources()

        self.assertEqual(
            [project["name"] for project in state["projects"]],
            ["User Project", DEFAULT_BOOTSTRAP_PROJECT["name"]],
        )
        self.assertEqual(
            [source["project_id"] for source in state["sources"]],
            [8, 8, 8],
        )
        self.assertEqual(state["commits"], 1)

    def test_bootstrap_default_project_and_sources_is_idempotent(self) -> None:
        state = {
            "projects": [
                {
                    "id": 3,
                    "name": DEFAULT_BOOTSTRAP_PROJECT["name"],
                    "keywords": [],
                    "exclude_keywords": [],
                    "risk_words": [],
                    "created_at": datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
                }
            ],
            "sources": [
                {
                    "id": 1,
                    "project_id": 3,
                    "source_type": DEFAULT_BOOTSTRAP_SOURCES[0]["source_type"],
                    "source_config": copy.deepcopy(
                        DEFAULT_BOOTSTRAP_SOURCES[0]["source_config"]
                    ),
                    "is_active": DEFAULT_BOOTSTRAP_SOURCES[0]["is_active"],
                    "poll_interval_s": DEFAULT_BOOTSTRAP_SOURCES[0]["poll_interval_s"],
                }
            ],
            "mentions_count": {},
            "commits": 0,
        }
        store = self._build_store(state)

        store.bootstrap_default_project_and_sources()
        store.bootstrap_default_project_and_sources()

        self.assertEqual(len(state["projects"]), 1)
        self.assertEqual(len(state["sources"]), len(DEFAULT_BOOTSTRAP_SOURCES))
        self.assertEqual(state["commits"], 1)

    def test_list_projects_returns_default_project_first(self) -> None:
        state = {
            "projects": [
                {
                    "id": 10,
                    "name": "User Project",
                    "keywords": ["bank"],
                    "exclude_keywords": [],
                    "risk_words": [],
                    "created_at": datetime(2026, 3, 16, 18, 0, tzinfo=UTC),
                },
                {
                    "id": 2,
                    "name": DEFAULT_BOOTSTRAP_PROJECT["name"],
                    "keywords": [],
                    "exclude_keywords": [],
                    "risk_words": [],
                    "created_at": datetime(2026, 3, 10, 9, 0, tzinfo=UTC),
                },
            ],
            "sources": self._default_sources_for_project(2),
            "mentions_count": {2: 5, 10: 1},
            "commits": 0,
        }
        store = self._build_store(state)

        projects = store.list_projects()

        self.assertEqual(projects[0]["name"], DEFAULT_BOOTSTRAP_PROJECT["name"])
        self.assertEqual(projects[0]["sources_count"], 3)
        self.assertEqual(projects[0]["mentions_count"], 5)
        self.assertEqual(projects[1]["name"], "User Project")
