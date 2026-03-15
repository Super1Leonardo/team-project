import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.dependencies import (
    get_app_settings,
    get_brandradar_clickhouse_store,
    get_brandradar_postgres_store,
    get_brandradar_runtime,
    get_messages_repository,
    get_ml_results_repository,
    get_sources_repository,
)
from backend.app.api.router import api_router
from backend.app.core.exception_handlers import register_exception_handlers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_app_settings()
    settings.telegram_session_path.parent.mkdir(parents=True, exist_ok=True)
    get_sources_repository().init_db()
    get_ml_results_repository().init_db()
    get_brandradar_postgres_store().init_db()
    try:
        get_messages_repository().init_db()
    except Exception:
        logger.exception("Raw messages ClickHouse init failed; continuing in degraded mode.")
    try:
        get_brandradar_clickhouse_store().init_db()
    except Exception:
        logger.exception("Mention events ClickHouse init failed; continuing in degraded mode.")
    runtime = get_brandradar_runtime()
    stop_event = asyncio.Event()
    worker_tasks = [
        asyncio.create_task(
            runtime.collector_worker.run_forever(stop_event),
            name="brandradar-collector-worker",
        ),
        asyncio.create_task(
            runtime.ml_worker.run_forever(stop_event),
            name="brandradar-ml-worker",
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
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
