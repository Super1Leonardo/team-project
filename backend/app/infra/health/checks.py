from __future__ import annotations

from time import perf_counter

from app.common.enums import ComponentHealthStatus
from app.infra.db.session import DatabaseManager
from app.infra.redis.client import RedisClient
from app.ports.collector import CollectorPort
from app.ports.health import HealthCheckResult
from app.ports.ml import MLPort


async def check_api() -> HealthCheckResult:
    started_at = perf_counter()
    latency_ms = int((perf_counter() - started_at) * 1000)
    return HealthCheckResult(
        component_name="api",
        component_type="application",
        status=ComponentHealthStatus.HEALTHY,
        latency_ms=latency_ms,
        meta={"mode": "in_process"},
    )


async def check_database(database_manager: DatabaseManager) -> HealthCheckResult:
    ok, detail, latency_ms, meta = await database_manager.ping()
    return HealthCheckResult(
        component_name="db",
        component_type="database",
        status=ComponentHealthStatus.HEALTHY if ok else ComponentHealthStatus.DOWN,
        latency_ms=latency_ms,
        last_error=detail,
        meta=meta,
    )


async def check_redis(redis_client: RedisClient) -> HealthCheckResult:
    started_at = perf_counter()
    try:
        ok = await redis_client.ping()
        latency_ms = int((perf_counter() - started_at) * 1000)
        return HealthCheckResult(
            component_name="redis",
            component_type="cache",
            status=ComponentHealthStatus.HEALTHY if ok else ComponentHealthStatus.DOWN,
            latency_ms=latency_ms,
            last_error=redis_client.init_error,
            meta={"mode": redis_client.mode},
        )
    except Exception as exc:
        latency_ms = int((perf_counter() - started_at) * 1000)
        return HealthCheckResult(
            component_name="redis",
            component_type="cache",
            status=ComponentHealthStatus.DOWN,
            latency_ms=latency_ms,
            last_error=str(exc),
            meta={"mode": redis_client.mode},
        )


async def check_ml(gateway: MLPort) -> HealthCheckResult:
    ok, detail, meta = await gateway.healthcheck()
    status = ComponentHealthStatus.HEALTHY if ok else ComponentHealthStatus.DEGRADED
    if meta and meta.get("mode") == "fallback":
        status = ComponentHealthStatus.DEGRADED
    return HealthCheckResult(
        component_name="ml_gateway",
        component_type="external_service",
        status=status,
        latency_ms=meta.get("latency_ms") if meta else None,
        last_error=detail,
        meta=meta or {},
    )


async def check_collector(gateway: CollectorPort) -> HealthCheckResult:
    ok, detail, meta = await gateway.healthcheck()
    status = ComponentHealthStatus.HEALTHY if ok else ComponentHealthStatus.DEGRADED
    if meta and meta.get("mode") == "stub":
        status = ComponentHealthStatus.DEGRADED
    return HealthCheckResult(
        component_name="collector_gateway",
        component_type="external_service",
        status=status,
        latency_ms=meta.get("latency_ms") if meta else None,
        last_error=detail,
        meta=meta or {},
    )
