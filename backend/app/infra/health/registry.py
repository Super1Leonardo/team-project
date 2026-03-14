from __future__ import annotations

from app.infra.db.session import DatabaseManager
from app.infra.health.checks import check_api, check_collector, check_database, check_ml, check_redis
from app.infra.redis.client import RedisClient
from app.ports.collector import CollectorPort
from app.ports.health import HealthCheckResult
from app.ports.ml import MLPort


class HealthRegistry:
    def __init__(
        self,
        database_manager: DatabaseManager,
        redis_client: RedisClient,
        ml_gateway: MLPort,
        collector_gateway: CollectorPort,
    ) -> None:
        self.database_manager = database_manager
        self.redis_client = redis_client
        self.ml_gateway = ml_gateway
        self.collector_gateway = collector_gateway

    async def run_checks(self) -> list[HealthCheckResult]:
        return [
            await check_api(),
            await check_database(self.database_manager),
            await check_redis(self.redis_client),
            await check_ml(self.ml_gateway),
            await check_collector(self.collector_gateway),
        ]
