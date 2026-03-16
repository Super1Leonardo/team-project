from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace

from backend.app.modules.brandradar.service import BrandRadarService


class _HealthyStore:
    def __init__(self) -> None:
        self.count_calls = 0

    def count_unprocessed_raw_posts(self) -> int:
        self.count_calls += 1
        return 7


class _HealthyClickHouseStore:
    def ping(self) -> None:
        return None


class _UnhealthyMLGateway:
    predict_url = "http://ml.example/predict"

    async def get_health_status(self) -> dict[str, str | None]:
        return {
            "status": "unhealthy",
            "url": self.predict_url,
            "error": "connection refused",
        }


class HealthServiceTests(unittest.TestCase):
    def test_get_health_reports_ml_status_and_error(self) -> None:
        store = _HealthyStore()
        runtime = SimpleNamespace(
            postgres_store=store,
            clickhouse_store=_HealthyClickHouseStore(),
            external_ml_gateway=_UnhealthyMLGateway(),
        )
        service = BrandRadarService(runtime)

        result = asyncio.run(service.get_health())

        self.assertEqual(
            result,
            {
                "status": "degraded",
                "postgres": "healthy",
                "clickhouse": "healthy",
                "ml": "unhealthy",
                "ml_url": "http://ml.example/predict",
                "ml_error": "connection refused",
                "ml_queue_size": 7,
            },
        )
        self.assertEqual(store.count_calls, 1)

    def test_get_health_uses_short_ttl_cache(self) -> None:
        store = _HealthyStore()
        runtime = SimpleNamespace(
            postgres_store=store,
            clickhouse_store=_HealthyClickHouseStore(),
            external_ml_gateway=_UnhealthyMLGateway(),
        )
        runtime.external_ml_gateway.settings = SimpleNamespace(
            backend_health_cache_ttl_seconds=2.0
        )
        service = BrandRadarService(runtime)

        first = asyncio.run(service.get_health())
        second = asyncio.run(service.get_health())

        self.assertEqual(first, second)
        self.assertEqual(store.count_calls, 1)
