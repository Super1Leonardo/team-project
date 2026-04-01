import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from backend.app.api.dependencies import (
    get_app_settings,
    get_brandradar_clickhouse_store,
    get_brandradar_postgres_store,
    get_brandradar_runtime,
)
from backend.app.api.router import api_router
from backend.app.core.exception_handlers import register_exception_handlers
from backend.app.core.observability import (
    RequestMetricsTracker,
    install_request_metrics_middleware,
    log_request_metrics_forever,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_app_settings()
    get_brandradar_postgres_store().init_db()
    try:
        get_brandradar_clickhouse_store().init_db()
    except Exception:
        logger.exception("Mention events ClickHouse init failed; continuing in degraded mode.")
    runtime = get_brandradar_runtime()
    stop_event = asyncio.Event()
    tracker = app.state.request_metrics_tracker
    worker_tasks = [
        asyncio.create_task(
            runtime.collector_worker.run_forever(stop_event),
            name="brandradar-collector-worker",
        ),
        asyncio.create_task(
            runtime.ml_worker.run_forever(stop_event),
            name="brandradar-ml-worker",
        ),
        asyncio.create_task(
            log_request_metrics_forever(
                stop_event=stop_event,
                tracker=tracker,
                interval_seconds=settings.backend_metrics_log_interval_seconds,
            ),
            name="brandradar-http-metrics",
        ),
    ]
    app.state.brandradar_runtime = runtime
    app.state.brandradar_worker_stop_event = stop_event
    app.state.brandradar_worker_tasks = worker_tasks

    try:
        yield
    finally:
        stop_event.set()
        await asyncio.gather(*worker_tasks, return_exceptions=True)


def create_app() -> FastAPI:
    settings = get_app_settings()
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        GZipMiddleware,
        minimum_size=1_000,
    )
    install_request_metrics_middleware(
        app,
        tracker=RequestMetricsTracker(
            window_seconds=settings.backend_metrics_window_seconds,
        ),
        slow_request_threshold_ms=settings.backend_slow_request_threshold_ms,
    )
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
