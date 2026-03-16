from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace

from backend.app.modules.brandradar.service import BrandRadarService


class _HealthyStore:
    def ping(self) -> None:
        return None

    def count_unprocessed_raw_posts(self) -> int:
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
        runtime = SimpleNamespace(
            postgres_store=_HealthyStore(),
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
